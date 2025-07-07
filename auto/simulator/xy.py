import time
from logging import info, error, debug, warning
from typing import Optional, Tuple, List

import pyautogui

from auto.ocr import working
from auto.ocr.req import ocr_list, TbpuParser, OcrDict, TextBox
from auto.ocr.str import score, position
from auto.ocr.str.score import contain

# Global variables for debugging and state management
pyautogui.FAILSAFE = False
last_screenshot_path: str = "../src/last_screenshot.png"
last_coordinates: Tuple[float, float] = (0, 0)
CONFIDENCE: float = 0.2


def key_value_score(key: str, value: str, similarity: float) -> float:
    full_line: Optional[TextBox] = get_text_detail(key, similarity, tbpu_parser=TbpuParser.BY_LINE)
    debug(f"full_line: {full_line} key: {key}")
    if not full_line or 'text' not in full_line:
        error(f"has no text in full_line: {full_line}")
        return 0
    return contain(value, full_line['text'])


def get_text_detail(
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        crop_region: Optional[List[Optional[int]]] = None,
) -> Optional[TextBox]:
    """
    Get detailed information about target text in current window
    """
    debug(f"[get_text_details] Getting details for: '{target_str}'")

    screenshot_path: Optional[str] = take_screenshot(crop_region)
    if not screenshot_path:
        error(f"Failed to capture screenshot screenshot_path: {screenshot_path}")
        return None

    return _find_text_detail(screenshot_path, target_str, similarity, tbpu_parser, crop_region=crop_region)


def get_text_details(
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        crop_region: Optional[List[Optional[int]]] = None,
) -> List[TextBox]:
    """
    Get detailed information about target text in current window
    """
    debug(f"[get_text_details] Getting details for: '{target_str}'")

    screenshot_path: Optional[str] = take_screenshot(crop_region)
    if not screenshot_path:
        error(f"Failed to capture screenshot screenshot_path: {screenshot_path}")
        return []

    return _find_text_details(screenshot_path, target_str, similarity, tbpu_parser, crop_region=crop_region)


def _calibrate_center(details: TextBox, target_str: str) -> TextBox:
    """
    text_details['center'] only shows the center of the bounding box
    this function will calibrate the center to the center of the target_str
    """
    box = details['box']
    #  text_details['center'] is the center of the target_str instead of center of the bounding box
    position_list = position.center_position(target_str, details['text'])
    if len(position_list) == 0:
        return details
    target_position = position_list[0]
    if len(position_list) > 1:
        warning(f"Multiple center positions found for '{target_str}': {position_list}")
    left = box[0][0]
    right = box[2][0]
    details['center'][0] = left + target_position * (right - left)

    return details


def _find_text_detail(
        file_path: str,
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        confidence: float = 0.5,
        crop_region: Optional[List[Optional[int]]] = None
) -> Optional[TextBox]:
    """
    Find target text in an image file and return basic match information

    Args:
        file_path (str): Path to image file
        target_str (str): Text to search for
        similarity (float): Minimum similarity score (0-1)
        confidence (float): Minimum confidence (0-1)
        crop_region (list): Optional crop region [x, y, width, height]

    Returns:
        dict: Basic match info with keys: text, score, similarity, box
              Returns None if no match found
    """

    def valuable(_entry: TextBox) -> bool:
        info(f"{len(score.clean(_entry['text']))} >= {len(target_str)} * 0.8 and {_entry['score']} >= {confidence}")
        return True
        return len(score.clean(_entry['text'])) >= len(target_str) * 0.8 and _entry['score'] >= confidence

    target_str = target_str.strip()
    debug(f"[find_text_details] Searching for: '{target_str}' file_path: {file_path}")

    result: Optional[OcrDict] = ocr_list(file_path, crop_region, tbpu_parser=tbpu_parser)
    if not result or result['code'] != 100:
        debug(f"[ERROR] OCR failed {result}")
        return None

    best_match: Optional[TextBox] = None
    best_score: float = 0.006

    for entry in result['data']:
        if entry['score'] > confidence:
            entry_text: str = entry['text']
            _similarity: float = score.match(target_str, entry_text)

            if _similarity >= best_score:
                info(f"Found match: similarity: {_similarity:.2f} (score: {entry['score']:.2f}) {entry['text']}")
                best_score = _similarity
                if _similarity > similarity and valuable(entry):
                    best_match = entry
                    best_match['similarity'] = _similarity
                else:
                    info(f"Discarded match: similarity: {_similarity:.2f} valuable: {valuable(entry)}")

    if not best_match:
        warning(f"No match found for '{target_str}' with similarity ≥ {similarity}")
        info(f"text of all matches: {[entry['text'] for entry in result['data']]}")
        return None

    warning(f"Found match: {best_match['text']} (similarity: {best_match['similarity']:.2f})")
    return _calibrate_center(best_match, target_str)


def _find_text_details(
        file_path: str,
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        confidence: float = 0.5,
        crop_region: Optional[List[Optional[int]]] = None,
) -> List[TextBox]:
    """
    Find all occurrences of target text in an image file with similarity > threshold

    Args:
        file_path (str): Path to image file
        target_str (str): Text to search for
        similarity (float): Minimum similarity score (0-1)
        confidence (float): Minimum confidence (0-1)
        crop_region (list): Optional crop region [x, y, width, height]

    Returns:
        List[TextBox]: List of matches with details, each containing:
            - text: Matched text
            - score: Confidence score
            - similarity: Similarity score
            - box: Bounding box coordinates
            - center: Center coordinates of the match
    """

    def valuable(_entry: TextBox) -> bool:
        return len(score.clean(_entry['text'])) >= len(target_str) * 0.8 and _entry['score'] >= confidence

    target_str = target_str.strip()
    debug(f"[_find_text_details] Searching for all occurrences of: '{target_str}' in file: {file_path}")

    result: Optional[OcrDict] = ocr_list(file_path, crop_region, tbpu_parser=tbpu_parser)
    if not result or result['code'] != 100:
        debug(f"[ERROR] OCR failed {result}")
        return []

    matches: List[TextBox] = []

    for entry in result['data']:
        if entry['score'] >= confidence:
            entry_text: str = entry['text']
            _similarity: float = score.match(target_str, entry_text)

            if _similarity > similarity and valuable(entry):
                match = entry.copy()
                match['similarity'] = _similarity
                match = _calibrate_center(match, target_str)
                matches.append(match)
                debug(f"Found match (similarity: {_similarity:.2f}): {entry_text}")

    if not matches:
        debug(f"No matches found for '{target_str}' with similarity > {similarity}")
    else:
        debug(f"Found {len(matches)} matches for '{target_str}' with similarity > {similarity}")

    return matches


def _coordinate(
        file_path: str,
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        confidence: float = 0.7,
        crop_region: Optional[List[Optional[int]]] = None
) -> Optional[Tuple[float, float]]:
    """
    Get coordinates of target text in an image file

    Args:
        file_path (str): Path to image file
        target_str (str): Text to search for
        similarity (float): Minimum similarity score (0-1)
        confidence (float): Minimum confidence (0-1)
        crop_region (list): Optional crop region [x, y, width, height]

    Returns:
        tuple: (x, y) coordinates of text center if found, None otherwise
    """
    global last_coordinates

    result: Optional[TextBox] = (
        _find_text_detail(file_path, target_str, similarity, tbpu_parser, confidence, crop_region))
    info(f"[find_text_details] Result: {result}")
    if not result:
        return None

    # 直接使用OCR结果中的center坐标
    # print(result['center'])
    center_x: float
    center_y: float
    center_x, center_y = result['center']
    last_coordinates = (center_x, center_y)

    return last_coordinates


def take_screenshot(crop_region: Optional[List[Optional[int]]] = None) -> Optional[str]:
    """
    Take screenshot of active window and save to file, with optional cropping.
    """
    if crop_region is None:
        crop_region = []
    global last_screenshot_path

    if not working.window:
        working.get_active_window()
    window = working.window
    # debug(f"[screenshot] Capturing window: {window.title}")
    # debug(f"[screenshot] Position: ({window.left}, {window.top})")
    debug(f"[screenshot] Dimensions: {window.width}x{window.height}")

    # Parse crop region (default to full window if not specified)
    crop_x: Optional[int] = crop_region[0] if len(crop_region) > 0 else None
    crop_y: Optional[int] = crop_region[1] if len(crop_region) > 1 else None
    crop_width: Optional[int] = crop_region[2] if len(crop_region) > 2 else None
    crop_height: Optional[int] = crop_region[3] if len(crop_region) > 3 else None

    # Calculate capture region
    left: int = window.left + (crop_x if crop_x is not None else 0)
    top: int = window.top + (crop_y if crop_y is not None else 0)
    # Calculate width - fixed logic
    width: int
    if crop_width is not None:
        if crop_x is not None:
            width = min(crop_width, window.width - crop_x)
        else:
            width = min(crop_width, window.width)
    else:
        width = window.width - (crop_x if crop_x is not None else 0)

    # Calculate height - fixed logic
    height: int
    if crop_height is not None:
        if crop_y is not None:
            height = min(crop_height, window.height - crop_y)
        else:
            height = min(crop_height, window.height)
    else:
        height = window.height - (crop_y if crop_y is not None else 0)

    # Debug output if any cropping is applied
    if any(param is not None for param in [crop_x, crop_y, crop_width, crop_height]):
        debug(f"[screenshot] Crop region: {crop_region}")
        debug(f"[screenshot] Final capture region: ({left}, {top}, {width}, {height})")

    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screenshot.save(last_screenshot_path)

    # debug(f"[screenshot] Saved to: {last_screenshot_path}")
    # debug(f"[screenshot] File size: {os.path.getsize(last_screenshot_path) / 1024:.1f} KB")

    return last_screenshot_path


def get_coordinates(
        target_str: str,
        similarity: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        crop_region: Optional[List[Optional[int]]] = None
) -> Optional[Tuple[float, float]]:
    """
    Get coordinates of target text in current window

    Args:
        target_str (str): Text to find
        similarity (float): Minimum confidence score (0-1)
        tbpu_parser (TbpuParser): TBPU parser
        crop_region (list): Optional crop region [x, y, width, height]

    Returns:
        tuple: (x, y) screen coordinates if successful, None otherwise
    """
    debug(f"[get_coordinates] Starting search for: '{target_str}'")

    screenshot_path: Optional[str] = take_screenshot(crop_region)
    if not screenshot_path:
        error("Failed to capture screenshot")
        return None

    img_coords: Optional[Tuple[float, float]] = _coordinate(
        screenshot_path, target_str, similarity, tbpu_parser=tbpu_parser, crop_region=crop_region)
    if not img_coords:
        error(f"Could not locate text: '{target_str}'")
        return None

    window = working.window
    # Get active window for offset
    if not window:
        error("Active window disappeared")
        return None

    # Convert to screen coordinates
    screen_x: float = window.left + img_coords[0]
    screen_y: float = window.top + img_coords[1]

    debug(f"[get_coordinates] Final screen coords: ({screen_x:.1f}, {screen_y:.1f})")
    return screen_x, screen_y


def move_mouse_to(
        target_str: str,
        confidence: float = 0.2,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        crop_region: Optional[List[Optional[int]]] = None
) -> bool:
    """
    Move mouse to target text in current window

    Args:
        target_str (str): Text to move mouse to
        confidence (float): Minimum confidence score (0-1)
        crop_region (list): Optional crop region [x, y, width, height]

    Returns:
        bool: True if movement successful, False otherwise
    """
    global last_coordinates

    coords: Optional[Tuple[float, float]] = get_coordinates(target_str, confidence, tbpu_parser=tbpu_parser,
                                                            crop_region=crop_region)
    if not coords:
        return False

    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
    last_coordinates = coords
    debug(f"[move_mouse_to] Mouse moved successfully")
    return True


def click_mouse(dx: int = 0, dy: int = 0) -> bool:
    """
    Click at current mouse position or last known coordinates

    Args:
        dx (int): X offset from last coordinates
        dy (int): Y offset from last coordinates

    Returns:
        bool: True if click successful, False otherwise
    """
    global last_coordinates

    if last_coordinates:
        x, y = last_coordinates
        debug(f"[click_mouse] Clicking at stored coordinates: ({x:.1f}, {y:.1f})")
        pyautogui.click(x + dx, y + dy)
    else:
        current_x, current_y = pyautogui.position()
        debug(f"[click_mouse] Clicking at current position: ({current_x}, {current_y})")
        pyautogui.click()

    debug(f"[click_mouse] Click successful")
    return True


if __name__ == "__main__":
    # Example usage
    target_text: str = "Successfully"
    crop_area: List[Optional[int]] = [None, None, 800, 600]  # x, y, width, height

    # Get text details
    text_details: Optional[TextBox] = get_text_detail(target_text, CONFIDENCE, crop_region=crop_area)
    print(f"[_coordinate_details] Found {text_details}")
    if text_details:
        print("\nText details found:")
        print(f"Text: {text_details['text']}")
        print(f"Similarity: {text_details['similarity']:.2f}")
        print(f"Center: {text_details['center']}")

    # Move and click
    if move_mouse_to(target_text, CONFIDENCE):
        info(f"\nSuccessfully moved to text: '{target_text}'")
        if click_mouse():
            info("Click successful!")
            time.sleep(0.2)
    else:
        info(f"\nFailed to find or move to text: '{target_text}'")
