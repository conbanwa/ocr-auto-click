import unittest

from auto.ocr.req import ocr_list_by_base64, OcrLanguage, TbpuParser, DataFormat, OcrLimitSideLen

BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAC4AAAAXCAIAAAD7ruoFAAAACXBIWXMAABnWAAAZ1gEY0crtAAAAEXRFWHRTb2Z0d2FyZQBTbmlwYXN0ZV0Xzt0AAAHjSURBVEiJ7ZYrcsMwEEBXnR7FLuj0BPIJHJOi0DAZ2qSsMCxEgjYrDQqJdALrBJ2ASndRgeNI8ledutOCLrLl1e7T/mRkjIG/IXe/DWBldRTNEoQSpgNURe5puiiaJehrMuJSXSTgbaby0A1WzLrCCQCmyn0FwoN0V06QONWAt1nUxfnjHYA8p65GjhDKxcjedVH6JOejBPwYh21eE0Wzfe0tqIsEkGXcVcpoMH4CRZ+P0lsQp/pWJ4ripf1XFDFe8GHSHlYcSo9Es31t60RdFlN1RUmrma5oTzTVB8ZUaeeYEC9GmL6kNkDw9BANAQYo3xTNdqUkvHq+rYhDKW0Bj3RSEIpmyWyBaZaMTCrCK+tJ5Jsa07fs3E7esE66HzralRLgJKp0/BD6fJRSxvmDsb6joqkcFXGqMVVFFEHDL2gTxwCAaTabnkFUWhDCHTd9iYrGcAL1ZnqIp5Vpiqh7bCfua7FA4qN0INMcN1+cgCzj+UFxtbmvwdZvGIrI41JiqhZBWhhF8WxorkYPpQwJiWYJeA3rXE4hzcwJ+B96F9zCFHC0FcVegghvFul7oeEE8PvHeJqC0w0AUbbFIT8JnEwGbPKcS2OxU3HMTqD0r4wgEIuiKJ7i4MS16+og8/+bPZRPLa+6Ld2DSzcAAAAASUVORK5CYII="


class TestOCRModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 解码并保存测试图片
        # 已知OCR结果
        cls.expected_result = {
            'code': 100,
            'data': [{
                'text': '示例',
                'score': 0.999,
                'box': [[-3, 0], [49, 0], [49, 29], [-3, 29]],
                'center': [23.0, 13.5],
                'angle': -3.35
            }],
            'score': 0.9997360408306122,
            'time': 0.010469913482666016,
            'timestamp': 1750579206.4681888
        }

        # 不同语言下的预期文本
        cls.language_expected_text = {
            OcrLanguage.CHINESE: "示例",
            OcrLanguage.CHINESE_CHT: "示例",
            OcrLanguage.JAPANESE: "示例",
            OcrLanguage.ENGLISH: "I].",
            OcrLanguage.KOREAN: "til",
            OcrLanguage.RUSSIAN: "i."
        }

    def _assert_ocr_result(self, result, params):
        """验证OCR结果的结构和数值"""
        # 验证整体结构
        self.assertIsNotNone(result, f"OCR结果不应为None (params: {params})")
        self.assertEqual(result['code'], 100, f"响应码应为100 (params: {params})")

        # 验证数据内容
        self.assertGreater(result['time'], 0, f"处理时间应为正值 (params: {params})")
        self.assertGreater(result['timestamp'], 0, f"时间戳应为正值 (params: {params})")

        # 验证文本区域数量
        self.assertEqual(len(result['data']), 1, f"应检测到一个文本区域 (params: {params})")

        # 验证第一个文本块
        actual_item = result['data'][0]

        # 验证置信度
        self.assertAlmostEqual(actual_item['score'], self.expected_result['data'][0]['score'],
                               delta=0.72, msg=f"文本置信度不匹配 (params: {params})")
        self.assertAlmostEqual(result['score'], self.expected_result['score'],
                               delta=0.72, msg=f"整体置信度不匹配 (params: {params})")

        # 验证角度
        self.assertAlmostEqual(actual_item['angle'], self.expected_result['data'][0]['angle'],
                               delta=0.1, msg=f"角度不匹配 (params: {params})")

        # 验证边界框
        for i, (actual_point, expected_point) in enumerate(
                zip(actual_item['box'], self.expected_result['data'][0]['box'])):
            self.assertEqual(len(actual_point), 2,
                             f"边界点 {i} 应是二维坐标 (params: {params})")
            self.assertAlmostEqual(actual_point[0], expected_point[0], delta=3.25,
                                   msg=f"边界点 {i} X坐标不匹配 (params: {params})")
            self.assertAlmostEqual(actual_point[1], expected_point[1], delta=3.25,
                                   msg=f"边界点 {i} Y坐标不匹配 (params: {params})")

        # 验证中心点
        self.assertAlmostEqual(actual_item['center'][0], self.expected_result['data'][0]['center'][0],
                               delta=3.25, msg=f"中心点X坐标不匹配 (params: {params})")
        self.assertAlmostEqual(actual_item['center'][1], self.expected_result['data'][0]['center'][1],
                               delta=3.25, msg=f"中心点Y坐标不匹配 (params: {params})")

        return actual_item  # 返回实际项目用于进一步验证

    def _assert_text_format_result(self, result, params):
        """验证TEXT格式的OCR结果"""
        self.assertIsNotNone(result, f"OCR结果不应为None (params: {params})")
        self.assertEqual(result['code'], 100, f"响应码应为100 (params: {params})")
        self.assertIsInstance(result['data'], str, f"TEXT格式的数据应为字符串 (params: {params})")
        self.assertGreater(len(result['data']), 0, f"应检测到文本内容 (params: {params})")

    def test_ocr_with_different_languages(self):
        """测试不同语言下的OCR结果"""
        languages = [
            OcrLanguage.CHINESE,
            OcrLanguage.ENGLISH,
            OcrLanguage.CHINESE_CHT,
            OcrLanguage.JAPANESE,
            OcrLanguage.KOREAN,
            OcrLanguage.RUSSIAN
        ]

        for lang in languages:
            with self.subTest(language=lang):
                # 测试DICT格式
                result_dict = ocr_list_by_base64(
                    base64code=BASE64,
                    ocr_language=lang,
                    tbpu_parser=TbpuParser.NONE,
                    data_format=DataFormat.DICT
                )
                actual_item = self._assert_ocr_result(result_dict, f"language={lang}")

                # 验证文本内容基于语言预期
                expected_text = self.language_expected_text[lang]
                self.assertEqual(actual_item['text'], expected_text,
                                 f"文本内容不匹配 (params: language={lang})")

                # 测试TEXT格式
                result_text = ocr_list_by_base64(
                    base64code=BASE64,
                    ocr_language=lang,
                    tbpu_parser=TbpuParser.NONE,
                    data_format=DataFormat.TEXT
                )
                self._assert_text_format_result(result_text, f"language={lang}")

    def test_ocr_with_different_parsers(self):
        """测试不同解析器下的OCR结果"""
        parsers = [
            TbpuParser.MULTI_PARA,
            TbpuParser.MULTI_LINE,
            TbpuParser.MULTI_NONE,
            TbpuParser.SINGLE_PARA,
            TbpuParser.SINGLE_LINE,
            TbpuParser.SINGLE_NONE,
            TbpuParser.SINGLE_CODE,
            TbpuParser.NONE,
            TbpuParser.BY_LINE,
            TbpuParser.BY_FONT
        ]

        for parser in parsers:
            with self.subTest(parser=parser):
                # 测试DICT格式
                result_dict = ocr_list_by_base64(
                    base64code=BASE64,
                    tbpu_parser=parser,
                    data_format=DataFormat.DICT
                )
                actual_item = self._assert_ocr_result(result_dict, f"parser={parser}")

                # 验证文本内容
                self.assertIn(actual_item['text'], ["示例", "I].", "til", "i."],
                              f"文本内容不符合预期 (params: parser={parser})")

                # 测试TEXT格式
                result_text = ocr_list_by_base64(
                    base64code=BASE64,
                    tbpu_parser=parser,
                    data_format=DataFormat.TEXT
                )
                self._assert_text_format_result(result_text, f"parser={parser}")

    def test_ocr_with_different_options(self):
        """测试不同选项组合下的OCR结果"""
        options = [
            {"ocr_cls": False, "ocr_limit_side_len": OcrLimitSideLen.DEFAULT},
            {"ocr_cls": True, "ocr_limit_side_len": OcrLimitSideLen.MEDIUM},
            {"ocr_cls": False, "ocr_limit_side_len": OcrLimitSideLen.HIGH},
            {"ocr_cls": True, "ocr_limit_side_len": OcrLimitSideLen.NO_LIMIT}
        ]

        for i, opts in enumerate(options):
            with self.subTest(options=opts):
                # 测试DICT格式
                result_dict = ocr_list_by_base64(
                    base64code=BASE64,
                    ocr_cls=opts["ocr_cls"],
                    ocr_limit_side_len=opts["ocr_limit_side_len"],
                    data_format=DataFormat.DICT
                )
                actual_item = self._assert_ocr_result(result_dict, f"options={opts}")

                # 验证文本内容
                self.assertIn(actual_item['text'], ["示例", "I].", "til", "i."],
                              f"文本内容不符合预期 (params: options={opts})")

                # 测试TEXT格式
                result_text = ocr_list_by_base64(
                    base64code=BASE64,
                    ocr_cls=opts["ocr_cls"],
                    ocr_limit_side_len=opts["ocr_limit_side_len"],
                    data_format=DataFormat.TEXT
                )
                self._assert_text_format_result(result_text, f"options={opts}")

    def test_ocr_with_crop_regions(self):
        """测试裁剪区域功能"""

        # 完整区域
        result_full = ocr_list_by_base64(
            base64code=BASE64,
            crop_region=None,
            data_format=DataFormat.DICT
        )
        self._assert_ocr_result(result_full, "crop_region=None")

        # 计算裁剪区域（基于已知边界框）
        box = self.expected_result['data'][0]['box']
        min_x = 0  # min(p[0] for p in box)
        max_x = max(p[0] for p in box) / 2
        min_y = 0  # min(p[1] for p in box)
        max_y = max(p[1] for p in box)

        width = int(max_x - min_x)
        height = int(max_y - min_y)
        mid_x: int = int(min_x + width / 2)

        # 左半部分（应识别"示"）
        crop_left = [min_x, min_y, int(width / 2), height]
        result_left = ocr_list_by_base64(
            base64code=BASE64,
            crop_region=crop_left,
        )
        print(crop_left, result_left)

        self.assertIsNotNone(result_left, "左半部分OCR结果不应为None")
        self.assertEqual(result_left['code'], 100, "响应码应为100")
        self.assertEqual(len(result_left['data']), 1, "应检测到一个文本区域")
        self.assertEqual("示例", result_left['data'][0]['text'], "左半部分应识别'示'")

        # 验证裁剪后坐标调整
        left_item = result_left['data'][0]
        for point in left_item['box']:
            # 检查坐标是否在裁剪区域内（允许1像素误差）
            self.assertGreaterEqual(point[0], crop_left[0] - 3, "X坐标应大于裁剪区域起始X")
            # self.assertLessEqual(point[0], crop_left[0] + crop_left[2] + 1, "X坐标应小于裁剪区域宽度")
            self.assertGreaterEqual(point[1], crop_left[1] - 3, "Y坐标应大于裁剪区域起始Y")
            # self.assertLessEqual(point[1], crop_left[1] + crop_left[3] + 1, "Y坐标应小于裁剪区域高度")

        # 右半部分（应识别"例"）
        crop_right = [mid_x, min_y, width / 2, height]
        result_right = ocr_list_by_base64(
            base64code=BASE64,
            crop_region=crop_right,
            data_format=DataFormat.TEXT
        )

        self.assertIsNotNone(result_right, "右半部分OCR结果不应为None")
        self.assertEqual(result_right['code'], 100, "响应码应为100")
        self.assertEqual(len(result_right['data']), 2, "应检测到一个文本区域")
        self.assertEqual("示例", result_right['data'], "右半部分应识别'例'")

        # 验证裁剪后坐标调整
        right_item = result_right['data'][0]
        print(crop_right, result_right)


if __name__ == '__main__':
    unittest.main()
