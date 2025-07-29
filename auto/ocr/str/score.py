import re

from Levenshtein import ratio, distance


def clean(text):
    """Remove all non-alphanumeric characters from text and handle spaces intelligently:
    - Preserve spaces between English words
    - Remove spaces between non-English characters (Chinese, numbers)
    - Remove spaces between mixed language text (English-Chinese)
    """
    # First remove all unwanted characters (keeping English, Chinese, numbers, and spaces)
    cleaned = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff_\- ]', '', text.strip())

    # Process spaces:
    # 1. Replace multiple spaces with single space
    # 2. Remove spaces between any non-space combinations except English-English
    cleaned = re.sub(r' +', ' ', cleaned)  # First collapse multiple spaces

    # Iterate through the string to handle spaces intelligently
    chars = list(cleaned)
    i = 0
    while i < len(chars):
        if chars[i] == ' ':
            # Check characters before and after the space
            prev_is_english = i > 0 and chars[i - 1].isascii() and chars[i - 1].isalpha()
            next_is_english = i < len(chars) - 1 and chars[i + 1].isascii() and chars[i + 1].isalpha()

            # Only keep space if it's between two English letters
            if not (prev_is_english and next_is_english):
                del chars[i]
                continue
        i += 1

    return ''.join(chars).strip()


def match(target, entry):
    multiplier = 1
    # if not only English, Chinese, numbers, and spaces in target, do not use clean text
    if not target.isascii():
        clean_target = clean(target)
        clean_entry = clean(entry)
    else:
        clean_target = target
        clean_entry = entry
    if clean_target == clean_entry:
        multiplier = 5
        if target == entry:
            multiplier = 9.99
        return _weighted_average(target, entry) * multiplier
    full_coefficient = _weighted_average(target, entry)
    return _weighted_average(clean_target, clean_entry) * multiplier * (full_coefficient * 0.5 + 0.5)


def _weighted_average(target, entry):
    return levenshtein(target, entry) * 0.1 + contain(target, entry) * 0.9


def levenshtein(target, entry):
    """Calculate match score based on Levenshtein distance between cleaned texts"""
    # Clean both strings by removing symbols
    # Calculate Levenshtein distance
    lev_dist = distance(target, entry)
    max_len = max(len(target), len(entry))

    # Normalize distance to 0-1 range (0 = perfect match)
    normalized_dist = lev_dist / max_len if max_len > 0 else 0

    # Convert distance to similarity score (1 = perfect match, 0 = completely different)
    similarity = 1 - normalized_dist

    # Apply the similarity to the original score
    return similarity


# def containing(target, entry, on_unwanted_char=0.8):
#     return contain(target, entry, on_unwanted_char) * 0.8 + 0.2


def contain(short, long, on_unwanted_char=0.8):
    """Calculate containment score between texts with fuzzy matching.
    Returns 1.0 if target is fully contained in entry with high similarity,
    and a partial score for fuzzy matches.

    Args:
        short: The string to search for
        long: The text to search within
        on_unwanted_char: the max value of the score when the character is not English, Chinese, numbers, and spaces

    Returns:
        float: Containment score between 0 and 1
    """
    # Handle empty strings
    if not short:
        return 1.0 if not long else 0.0
    if not long:
        return 0.0

    # If both strings are non-empty and completely different, return 0.0
    # This handles cases like Chinese vs English where no substring can match
    if short and long:
        # Check if any character from short is in long or vice versa
        short_in_long = any(c in long for c in short)
        long_in_short = any(c in short for c in long)
        
        # If no characters match in either direction
        if not short_in_long and not long_in_short:
            return 0.0

    # Exact containment check
    if short in long:
        return 1.0


    # Split into words/tokens (handles both English and Chinese)
    target_tokens = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]', short)
    entry_tokens = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]', long)

    # Check for ordered token containment with fuzzy matching
    max_score = 0.0
    for i in range(len(entry_tokens) - len(target_tokens) + 1):
        window = entry_tokens[i:i + len(target_tokens)]
        window_text = ''.join(window)
        target_text = ''.join(target_tokens)

        # Calculate similarity ratio
        current_score = ratio(target_text, window_text)

        # Update max score if above threshold
        if current_score >= on_unwanted_char:
            max_score = max(max_score, current_score)

    return max_score
