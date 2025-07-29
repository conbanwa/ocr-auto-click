import time
from logging import info, error

import pyautogui
import pyperclip

from auto.ocr.req import TbpuParser
from auto.ocr.working import get_active_window
from auto.simulator.xy import get_text_detail, click_mouse, get_coordinates, move_mouse_to


def switch_window():
    press('alt', 'tab')
    get_active_window()


def press(key1, key2='none', key3='none'):
    """
    Simulate simultaneous key press with support for up to 3 keys

    Args:
        key1 (str): Primary key to press
        key2 (str): Secondary key to press (default: 'none')
        key3 (str): Tertiary key to press (default: 'none')
    """
    key2 = key2.lower()
    key3 = key3.lower()
    
    if key2 == 'none' and key3 == 'none':
        pyautogui.press(key1)
        info(f"Pressed single key: {key1}")
    elif key3 == 'none':
        pyautogui.hotkey(key1, key2)
        info(f"Pressed combination: {key1}+{key2}")
    else:
        pyautogui.hotkey(key1, key2, key3)
        info(f"Pressed combination: {key1}+{key2}+{key3}")
    time.sleep(0.3)


def wait_for(confirm_text: str, is_click: bool = False, similarity=0.2, tbpu_parser=TbpuParser.NONE, overtime: float = 15,
             interval: float = 0.1) -> bool:
    """
    Wait for confirmation text to appear on screen

    Args:
        confirm_text: Text to wait for
        is_click: Whether to click on the text if found (default: False)
        similarity: Similarity threshold in percentage
        tbpu_parser: TBPU parser
        overtime: Maximum waiting time in seconds
        interval: Time between checks in seconds

    Returns:
        bool: True if text appears within timeout, False otherwise
    """
    if not confirm_text:
        return True

    info(f"Waiting for confirmation text: '{confirm_text}' (timeout: {overtime}s)")
    start_time = time.time()

    while time.time() - start_time < overtime:
        coords = get_coordinates(confirm_text, similarity=similarity, tbpu_parser=tbpu_parser)
        if coords:
            info(f"Confirmation text found: '{confirm_text}'")
            if is_click:
                x, y = coords
                pyautogui.click(x, y)
                info(f"Clicked at coordinates: ({x}, {y})")
            return True
        # keep waiting
        time.sleep(interval)

    info(f"Timeout: Confirmation text '{confirm_text}' not found within {overtime} seconds")
    return False


def scroll_until(target_text, max_scrolls=10, scroll_amount=-900):
    """
    Scroll the page until target text appears

    Args:
        target_text (str): Text to search for while scrolling
        max_scrolls (int): Maximum number of scroll attempts (default: 10)
        scroll_amount (int): Pixel amount to scroll (negative for down, positive for up)

    Returns:
        bool: True if text found, False if not found after max attempts
    """
    for _ in range(max_scrolls):
        if move_and_click(target_text):
            return True
        # Scroll down (negative value) or up (positive value)
        pyautogui.scroll(scroll_amount)
        time.sleep(0.5)  # Wait for scroll to complete
    print(f"Text '{target_text}' not found after {max_scrolls} scroll attempts")
    return False


def move_and_click(target_text: str, max_scrolls=0, confidence=0.1,
                   tbpu_parser=TbpuParser.NONE, offset_x: float = 0, offset_y: float = 0) -> bool:
    """
    Combined move, scroll and click operation with optional scrolling

    Args:
        target_text: Text to click on
        offset_x: X offset for click (as a percentage of the text width)
        offset_y: Y offset for click (as a percentage of the text height)
        max_scrolls: Maximum number of scroll attempts remaining (0 means no scrolling)
        tbpu_parser: Tbpu parser
        confidence: Confidence level for text detection

    Returns:
        bool: True if all steps succeed, False otherwise
    """
    # Get text details and click on the target
    detail = get_text_detail(target_text, confidence, tbpu_parser=tbpu_parser)
    if detail:
        info(f"\nFound target text: '{target_text}' {detail}")
        
        # Calculate click position based on text bounding box and offsets
        box = detail['box']
        box_width = box[2][0] - box[0][0]
        box_height = box[3][1] - box[0][1]
        dx, dy = int(box_width * offset_x), int(box_height * offset_y)
        
        # Get the center coordinates
        center_x, center_y = detail['center']
        
        # Move mouse to the target position and click
        target_x, target_y = center_x + dx, center_y + dy
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        info(f"Moved to: target: '{target_text}', position: ({target_x:.1f}, {target_y:.1f})")
        
        # Perform the click
        pyautogui.click()
        info(f"Clicked on: '{target_text}' at ({target_x:.1f}, {target_y:.1f})")
        time.sleep(0.2)
        return True
    else:
        error(f"Failed to move to: '{target_text}'")
    # If we still have scroll attempts left
    if max_scrolls > 0:
        if max_scrolls == 1:  # Only log this message on last scroll attempt
            info(f"Text not found, beginning scroll search (max {max_scrolls} attempts)...")

        pyautogui.scroll(-800)  #
        # pyautogui.press('pagedown')
        time.sleep(0.1)  # Wait for scroll to complete

        # Recursively try again with decremented max_scrolls
        return move_and_click(target_text, max_scrolls - 1, confidence, tbpu_parser, offset_x, offset_y)

    # If we've exhausted all scroll attempts
    info(f"Failed to find/move to: '{target_text}'")
    return False


def _is_all_ascii(text):
    return all(ord(c) < 128 for c in text)


def input_text(text):
    # 使用剪贴板复制粘贴（并恢复原始剪贴板内容）
    original_clipboard = pyperclip.paste()  # 保存当前剪贴板内容
    pyperclip.copy(text)  # 复制目标文本到剪贴板
    pyautogui.hotkey('ctrl', 'v')  # 粘贴
    pyperclip.copy(original_clipboard)  # 恢复剪贴板原始内容
    time.sleep(0.1)  # 等待粘贴完成


def write_text(text):
    if len(text) < 20 and _is_all_ascii(text):
        pyautogui.write(text, interval=0.02)
        return
    input_text(text)
