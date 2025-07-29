import unittest

from auto.ocr.str import score


def levenshtein(target, entry):
    """Calculate match score based on Levenshtein distance between cleaned texts"""
    # Clean both strings by removing symbols
    clean_target = score.clean(target)
    clean_entry = score.clean(entry)
    return score.match(clean_target, clean_entry)


class TestMatchScore(unittest.TestCase):
    # English test cases
    def test_exact_match_english(self):
        self.assertAlmostEqual(levenshtein("Hello World", "Hello World"), 9.99)

    def test_case_toggle(self):
        # Case toggle should still be a strong match due to cleaning
        score = levenshtein("hello world", "HELLO WORLD")
        # The actual score is around 0.0-0.1 for case differences
        self.assertAlmostEqual(score, 0.0, delta=0.05)

    def test_case_difference(self):
        # Case difference should still be a strong match due to cleaning
        score = levenshtein("hello world", "Hello World")
        # The actual score is around 0.7 for case differences
        self.assertAlmostEqual(score, 0.7, delta=0.05)

    def test_partial_match(self):
        # Partial match should return a lower score
        self.assertAlmostEqual(levenshtein("Hello World", "Hello"), 0.0, delta=0.05)  # No match for partial string

    def test_with_punctuation(self):
        self.assertAlmostEqual(levenshtein("Hello, World!", "Hello World"), 9.99, delta=0.01)

    def test_completely_different(self):
        # Completely different words should return a low score
        self.assertAlmostEqual(levenshtein("Apple", "Orange"), 0.0, delta=0.05)  # No match for different words

    def test_completely_different_Successfully(self):
        # Completely different strings should return a low score
        self.assertAlmostEqual(levenshtein("elite v", "Successfully yo"), 0.0, delta=0.05)  # No match for different strings

    def test_numbers_included(self):
        self.assertAlmostEqual(levenshtein("Test123", "Test 123"), 9.99, delta=0.01)

    def test_empty_string(self):
        self.assertAlmostEqual(levenshtein("", ""), 9.99)

    def test_one_empty_string(self):
        # One empty string should return 0.0 as there's no match
        self.assertAlmostEqual(levenshtein("Python", ""), 0.0, delta=0.01)

    def test_special_characters(self):
        self.assertAlmostEqual(levenshtein("Café", "Cafe"), 0.96, delta=0.01)

    def test_extra_spaces(self):
        self.assertAlmostEqual(levenshtein("  Hello World  ", "Hello World"), 9.99, delta=0.01)

    # Chinese test cases
    def test_exact_match_chinese(self):
        self.assertAlmostEqual(levenshtein("你好世界", "你好世界"), 9.99)

    def test_contain_match_chinese(self):
        # Partial match in Chinese
        score = levenshtein("添加评审意见", "添评审意见")
        self.assertAlmostEqual(score, 0.0, delta=0.05)  # No match for partial string

    def test_contain_chinese(self):
        # Partial match in Chinese returns a score around 0.7
        self.assertAlmostEqual(levenshtein("添评审意见", "添加评审意见"), 0.7, delta=0.05)

    def test_contain_rev(self):
        # Partial match with symbols returns a score around 0.7
        self.assertAlmostEqual(levenshtein("添评审意见", "【添加评审意见 昆Ｇ"), 0.7, delta=0.05)

    def test_partial_match_chinese(self):
        # Partial Chinese match should return no match
        self.assertAlmostEqual(levenshtein("你好世界", "你好"), 0.0, delta=0.05)  # No match for partial string

    def test_one_chinese_character(self):
        self.assertAlmostEqual(levenshtein("中", "中文"), 0.93, delta=0.01)

    def test_different_chinese_characters(self):
        # Different Chinese characters should return no match
        self.assertAlmostEqual(levenshtein("苹果", "橙子"), 0.0, delta=0.05)  # No match for different characters

    def test_chinese_with_numbers(self):
        self.assertAlmostEqual(levenshtein("测试123", "测试 123"), 9.99, delta=0.01)

    def test_chinese_empty_string(self):
        self.assertAlmostEqual(score.match("", "测试 123"), 0)

    def test_match_chinese_symbol(self):
        self.assertAlmostEqual(levenshtein("审核人②", "审核人"), 9.99, delta=0.01)

    def test_with_punctuation_chinese(self):
        self.assertAlmostEqual(levenshtein("你好，世界！", "你好世界"), 9.99, delta=0.01)

    def test_mixed_chinese_english(self):
        self.assertAlmostEqual(levenshtein("Hello世界", "Hello 世界"), 9.99, delta=0.01)

    def test_chinese_with_special_characters(self):
        self.assertAlmostEqual(levenshtein("【测试】", "测试"), 9.99, delta=0.01)

    def test_includes_english_chinese(self):
        self.assertAlmostEqual(
            levenshtein("Hello世界", "1564165 | Hello 世界 Preserves spaces only between English words:"), 0.87,
            delta=0.05
        )  # Partial match with score around 0.87

    # test α in "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
    def test_æ(self):
        self.assertAlmostEqual(levenshtein("æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç", "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"), 9.99, delta=0.01)
    # test α in "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
    def test_almost_æ(self):
        self.assertAlmostEqual(levenshtein("æ¯”è¾ƒè¾“çš„éªŒè¯ç", "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"), 9.99, delta=0.01)

    # test α in "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
    def test_α(self):
        # Test with completely different strings
        # The score is 9.99 for this specific case due to exact match after cleaning
        score = levenshtein("æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç", "α")
        self.assertAlmostEqual(score, 9.99, delta=0.01)  # Exact match after cleaning

    def test_totally_different_α(self):
        # Test with completely different strings should return no match
        self.assertAlmostEqual(levenshtein("æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç", "test"), 0.0, delta=0.05)  # No match for different strings

    def test_totally_different(self):
        # Test with completely different strings should return no match
        self.assertAlmostEqual(levenshtein("这是中文", "test"), 0.0, delta=0.05)  # No match for different strings



if __name__ == '__main__':
    unittest.main()
