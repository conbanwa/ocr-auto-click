import unittest

from auto.ocr import score


def levenshtein(target, entry):
    """Calculate match score based on Levenshtein distance between cleaned texts"""
    # Clean both strings by removing symbols
    clean_target = score.clean(target)
    clean_entry = score.clean(entry)
    return score.levenshtein(clean_target, clean_entry)


class TestMatchScore(unittest.TestCase):
    # English test cases
    def test_exact_match_english(self):
        self.assertAlmostEqual(levenshtein("Hello World", "Hello World"), 1.0)

    def test_case_difference(self):
        self.assertAlmostEqual(levenshtein("hello world", "Hello World"), 0.8181818181818181)

    def test_partial_match(self):
        self.assertAlmostEqual(levenshtein("Hello World", "Hello"), 0.45, delta=0.1)

    def test_with_punctuation(self):
        self.assertAlmostEqual(levenshtein("Hello, World!", "Hello World"), 1.0)

    def test_completely_different(self):
        self.assertAlmostEqual(levenshtein("Apple", "Orange"), 0.16, delta=0.1)

    def test_completely_different_Successfully(self):
        self.assertAlmostEqual(levenshtein(" elite v", "Successfully yo"), 0.16, delta=0.1)

    def test_numbers_included(self):
        self.assertAlmostEqual(levenshtein("Test123", "Test 123"), 1.0)

    def test_empty_string(self):
        self.assertAlmostEqual(levenshtein("", ""), 1.0)

    def test_one_empty_string(self):
        self.assertAlmostEqual(levenshtein("Python", ""), 0.0)

    def test_special_characters(self):
        self.assertAlmostEqual(levenshtein("Café", "Cafe"), 0.75, delta=0.01)

    def test_extra_spaces(self):
        self.assertAlmostEqual(levenshtein("  Hello World  ", "Hello World"), 1.0)

    # Chinese test cases
    def test_exact_match_chinese(self):
        self.assertAlmostEqual(levenshtein("你好世界", "你好世界"), 1.0)

    def test_contain_match_chinese(self):
        self.assertAlmostEqual(levenshtein("添加评审意见", "添评审意见"), 0.83, delta=0.01)

    def test_contain_chinese(self):
        self.assertAlmostEqual(levenshtein("添评审意见", "添加评审意见"), 0.83, delta=0.01)

    def test_match_chinese_symbol(self):
        self.assertAlmostEqual(levenshtein("审核人②", "审核人"), 1.0)

    def test_partial_match_chinese(self):
        self.assertAlmostEqual(levenshtein("你好世界", "你好"), 0.6, delta=0.1)

    def test_with_punctuation_chinese(self):
        self.assertAlmostEqual(levenshtein("你好，世界！", "你好世界"), 1.0)

    def test_mixed_chinese_english(self):
        self.assertAlmostEqual(levenshtein("Hello世界", "Hello 世界"), 1.0)

    def test_different_chinese_characters(self):
        self.assertAlmostEqual(levenshtein("苹果", "橙子"), 0.0)

    def test_chinese_with_numbers(self):
        self.assertAlmostEqual(levenshtein("测试123", "测试 123"), 1.0, delta=0.1)

    def test_chinese_empty_string(self):
        self.assertAlmostEqual(levenshtein("", ""), 1.0)

    def test_one_chinese_character(self):
        self.assertAlmostEqual(levenshtein("中", "中文"), 0.5, delta=0.01)

    def test_chinese_with_special_characters(self):
        self.assertAlmostEqual(levenshtein("【测试】", "测试"), 1.0)

    def test_traditional_vs_simplified(self):
        self.assertAlmostEqual(levenshtein("計算機", "计算机"), 0.333333333)

    def test_includes(self):
        self.assertAlmostEqual(
            levenshtein("Hello世界", "1564165 | Hello 世界 Preserves spaces only between English words:"), 0.12,
            delta=0.05)


if __name__ == '__main__':
    unittest.main()
