from typing import Optional, Tuple, List
import unicodedata

# Width ratio of Chinese characters to English characters
# This is an approximation - adjust based on your specific font
WIDTH_RATIO = 19/10

def _is_cjk(char: str) -> bool:
    """Check if a character is a CJK (Chinese, Japanese, Korean) character."""
    try:
        return unicodedata.name(char).startswith(('CJK UNIFIED', 'CJK COMPATIBILITY'))
    except ValueError:
        return False

def _get_visual_width(text: str) -> float:
    """Calculate the visual width of the text considering different character widths."""
    width = 0.0
    for char in text:
        if _is_cjk(char):
            width += WIDTH_RATIO
        else:
            # Basic Latin characters (including English letters, numbers, common symbols)
            if ord(char) <= 0x7F:
                width += 1.0
            # Full-width characters (including full-width numbers, letters, etc.)
            elif 0xFF00 <= ord(char) <= 0xFFEF:
                width += 2.0
            # Other characters (could be adjusted as needed)
            else:
                width += 1.0
    return width

def starts(target: str, entry: str) -> Optional[float]:
    """Calculate the position of the target text in the entry text.
    
    Args:
        target: The text to find
        entry: The text to search within
        
    Returns:
        float: Normalized visual position of target in entry (0 to 1), or None if not found
    """
    if not target or not entry:
        return None
        
    pos = entry.find(target)
    if pos == -1:
        return None
        
    # Calculate visual width of the prefix (text before the match)
    prefix = entry[:pos]
    visual_prefix_width = _get_visual_width(prefix)
    
    # Calculate total visual width of the entry
    total_visual_width = _get_visual_width(entry)
    
    # Return normalized visual position (0 to 1)
    return visual_prefix_width / total_visual_width if total_visual_width > 0 else 0.0


def ends(target: str, entry: str) -> Optional[float]:
    """Calculate the end position of the target text in the entry text.
    
    Args:
        target: The text to find
        entry: The text to search within
        
    Returns:
        float: Normalized visual end position of target in entry (0 to 1), or None if not found
    """
    if not target or not entry:
        return None
        
    pos = entry.find(target)
    if pos == -1:
        return None
        
    # Calculate visual width up to the end of the match
    text_up_to_end = entry[:pos + len(target)]
    visual_width = _get_visual_width(text_up_to_end)
    
    # Calculate total visual width of the entry
    total_visual_width = _get_visual_width(entry)
    
    # Return normalized visual end position (0 to 1)
    return visual_width / total_visual_width if total_visual_width > 0 else 0.0


def center_position(target: str, entry: str) -> List[float]:
    """Calculate the center positions of all occurrences of the target text in the entry text,
    considering different character widths between Chinese and English.
    
    Args:
        target: The text to find
        entry: The text to search within
        
    Returns:
        List[float]: List of normalized visual center positions (0 to 1) for each occurrence,
                    or empty list if not found
    """
    if not target or not entry:
        return []
        
    positions = []
    start = 0
    total_visual_width = _get_visual_width(entry)
    
    if total_visual_width == 0:
        return []
        
    target_len = len(target)
    entry_len = len(entry)
    
    while True:
        # Find next occurrence
        pos = entry.find(target, start)
        if pos == -1:
            break
            
        # Get the matched substring
        matched_text = entry[pos:pos + target_len]
        
        # Calculate visual positions
        visual_prefix_width = _get_visual_width(entry[:pos])
        visual_match_width = _get_visual_width(matched_text)
        
        # Calculate start and end positions in visual space
        visual_start = visual_prefix_width / total_visual_width
        visual_end = (visual_prefix_width + visual_match_width) / total_visual_width
        
        # Add the center point to the results
        center = (visual_start + visual_end) / 2
        positions.append(round(center, 8))  # Round to avoid floating point precision issues
        
        # Move start position for next search
        start = pos + 1
        if start >= entry_len:
            break
    
    return positions
