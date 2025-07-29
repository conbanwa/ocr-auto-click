from unittest import TestCase

from auto.ocr.str.score import contain
from auto.ocr.str.score import contain


class TestCalculateContainScore(TestCase):
    # English test cases
    def test_exact_match_english(self):
        self.assertAlmostEqual(contain("Hello", "Hello World"), 1.0)

    def test_case_insensitive_match(self):
        self.assertAlmostEqual(contain("hello", "Hello World"), 0.8)

    def test_partial_word_match(self):
        self.assertAlmostEqual(contain("Hell", "Hello World"), 1)

    def test_no_match_english(self):
        self.assertAlmostEqual(contain("Foo", "Hello World"), 0.0)

    def test_with_punctuation(self):
        self.assertAlmostEqual(contain("Hello", "Hello, World!"), 1.0)

    # Chinese test cases
    def test_contain_match_chinese(self):
        self.assertAlmostEqual(contain("添加评审意见", "添评审意见"), 0.0, delta=0.01)

    def test_contain_chinese(self):
        self.assertAlmostEqual(contain("添评审意见", "添加评审意见"), 0.8, delta=0.01)

    def test_exact_match_chinese(self):
        self.assertAlmostEqual(contain("你好", "你好世界"), 1.0)

    def test_partial_match_chinese(self):
        self.assertAlmostEqual(contain("你", "你好世界"), 1.0)

    def test_similar_chinese(self):
        self.assertAlmostEqual(contain("你世", "你好世界"), 0.0)

    def test_no_match_chinese(self):
        self.assertAlmostEqual(contain("再见", "你好世界"), 0.0)

    # Mixed language test cases
    def test_mixed_exact_match(self):
        self.assertAlmostEqual(contain("Hello世界", "Hello世界"), 1.0)

    def test_mixed_contained(self):
        self.assertAlmostEqual(contain("Hello", "Hello世界"), 1.0)

    def test_mixed_with_punctuation(self):
        self.assertAlmostEqual(contain("Hello世界", "【Hello世界】"), 1.0)

    def test_complex_mixed_case(self):
        self.assertAlmostEqual(
            contain("Hello世界", "1564165 | Hello 世界 Preserves spaces only between English words:"),
            1.0
        )

    # Edge cases
    def test_empty_target(self):
        self.assertAlmostEqual(contain("", "Hello World"), 0)

    def test_empty_entry(self):
        self.assertAlmostEqual(contain("Hello", ""), 0.0)

    def test_both_empty(self):
        self.assertAlmostEqual(contain("", ""), 1.0)

    def test_whitespace_only(self):
        self.assertAlmostEqual(contain(" ", "Hello World"), 1.0)

    # Fuzzy matching tests
    def test_fuzzy_english_match(self):
        self.assertAlmostEqual(contain("Helo", "Hello World"), 0.8, delta=0.1)

    def test_fuzzy_chinese_match(self):
        self.assertAlmostEqual(contain("你你", "你好世界"), 0)

    def test_threshold_adjustment(self):
        # Should return 0.0 when threshold is higher than match similarity
        self.assertAlmostEqual(contain("Helo", "Hello World", on_unwanted_char=0.9), 0.0)


class TestContainingFunction(TestCase):
    """Test cases for the contain function."""
    
    def test_containing_unicode_mojibake(self):
        # Test with mojibake string
        mojibake = "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
        self.assertAlmostEqual(contain(mojibake, mojibake), 1.0, delta=0.01)
        
    def test_containing_unicode_greek(self):
        # Test with Greek letter
        self.assertAlmostEqual(contain("æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç", "α"), 0.0, delta=0.01)
        
    def test_containing_unicode_english(self):
        # Test with English text against mojibake
        self.assertAlmostEqual(contain("æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç", "test"), 0.0, delta=0.01)
        
    def test_containing_chinese_english(self):
        # Test with Chinese text against English
        self.assertAlmostEqual(contain("这是中文", "test"), 0.0, delta=0.01)
        
    def test_containing_partial_mojibake(self):
        # Test with partial mojibake match
        mojibake = "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
        self.assertGreater(contain(mojibake, "æ¯”è¾ƒ"), 0.0)
        self.assertGreater(contain(mojibake, "éªŒè¯"), 0.0)

    def test_containing_partial_mojibake_reverse(self):
        # Test with partial mojibake match in reverse
        mojibake = "æ¯”è¾ƒè¾“å…¥çš„éªŒè¯ç"
        self.assertGreater(contain("æ¯”è¾ƒ", mojibake), 0.0)
        self.assertGreater(contain("éªŒè¯", mojibake), 0.0)
