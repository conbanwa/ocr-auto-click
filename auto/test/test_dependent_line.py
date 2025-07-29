import time
import unittest
from typing import List, Dict

from auto.ocr.req import ocr_list, TbpuParser, OcrLanguage, DataFormat
from auto.simulator.xy import take_screenshot


class TestLineGrouping(unittest.TestCase):
    # 可配置参数
    MAX_LINE_HEIGHT = 50  # 单行最大高度(px)
    ALLOWED_OVERLAP_RATIO = 0.4  # 允许的行高重叠比例(30%)
    MIN_MERGED_WORDS = 3  # 视为合并行的最小单词数
    WATERMARK_ANGLE_THRESHOLD = 6.0  # 角度超过此值视为水印文字(度)
    ALLOW_WATERMARK_OVERLAP = True  # 是否允许水印文字与其他文字重叠

    def test_line_grouping_with_overlap(self):
        """测试行分组，允许30%高度范围内的重叠，特殊处理水印文字"""
        time.sleep(1)
        take_screenshot()
        results = ocr_list(
            file_path='../src/test_screenshot.png',
            ocr_language=OcrLanguage.CHINESE,
            tbpu_parser=TbpuParser.BY_LINE,
            data_format=DataFormat.DICT
        )

        errors: List[str] = []
        line_info = self._collect_line_info(results, errors)

        if errors:
            self._fail_with_all_errors(errors, line_info)
            return

        self._validate_line_integrity(line_info, errors)
        self._validate_line_relationships(line_info, errors)
        self._validate_text_merging(line_info, errors)

        if errors:
            self._fail_with_all_errors(errors, line_info)

    def _collect_line_info(self, results, errors: List[str]) -> List[Dict]:
        """收集所有行的边界信息，标记水印行"""
        line_info = []

        if 'data' not in results:
            errors.append("OCR结果缺少'data'字段")
            return line_info

        if not results['data']:
            errors.append("未识别到任何文本行")
            return line_info

        for i, line in enumerate(results['data']):
            box = line['box']
            y_min, y_max = min(p[1] for p in box), max(p[1] for p in box)
            angle = abs(line['angle'])
            is_watermark = angle > self.WATERMARK_ANGLE_THRESHOLD

            line_info.append({
                'line_num': i + 1,
                'text': line['text'],
                'angle': line['angle'],
                'abs_angle': angle,
                'is_watermark': is_watermark,
                'words': line['text'].split(),
                'y_pos': line['center'][1],
                'y_min': y_min,
                'y_max': y_max,
                'height': y_max - y_min,
                'x_min': min(p[0] for p in box),
                'x_max': max(p[0] for p in box),
                'width': max(p[0] for p in box) - min(p[0] for p in box)
            })

        return line_info

    def _validate_line_integrity(self, line_info: List[Dict], errors: List[str]):
        """验证单行内部一致性"""
        for line in line_info:
            if line['height'] > self.MAX_LINE_HEIGHT and not line['is_watermark']:
                errors.append(
                    f"行 {line['line_num']} 高度异常: {line['height']:.1f}px "
                    f"(允许最大值: {self.MAX_LINE_HEIGHT}px)"
                )

            if not (line['y_min'] <= line['y_pos'] <= line['y_max']):
                errors.append(
                    f"行 {line['line_num']} 中心点Y值({line['y_pos']:.1f}) "
                    f"超出边界范围({line['y_min']:.1f}-{line['y_max']:.1f})"
                )

    def _validate_line_relationships(self, line_info: List[Dict], errors: List[str]):
        """验证行间关系，特殊处理水印文字"""
        for i in range(len(line_info) - 1):
            curr, next_ = line_info[i], line_info[i + 1]

            # 如果两行都是水印或者允许水印重叠，则跳过重叠检查
            if (curr['is_watermark'] and next_['is_watermark']) or \
                    (self.ALLOW_WATERMARK_OVERLAP and
                     (curr['is_watermark'] or next_['is_watermark'])):
                continue

            # X轴重叠检测
            x_overlap = (curr['x_max'] > next_['x_min'] and
                         next_['x_max'] > curr['x_min'])

            if x_overlap:
                allowed_overlap = min(curr['height'], next_['height']) * self.ALLOWED_OVERLAP_RATIO
                actual_overlap = max(0, curr['y_max'] - next_['y_min'])

                if actual_overlap > allowed_overlap:
                    errors.append(
                        f"行 {curr['line_num']}-{next_['line_num']} 重叠超出允许范围:\n"
                        f"  X轴重叠: {curr['x_min']:.1f}-{curr['x_max']:.1f} ↔ "
                        f"{next_['x_min']:.1f}-{next_['x_max']:.1f}\n"
                        f"  Y轴重叠: {actual_overlap:.1f}px (允许最大: {allowed_overlap:.1f}px)\n"
                        f"  上行高: {curr['height']:.1f}px | 下行高: {next_['height']:.1f}px\n"
                        f"  上行角度: {curr['angle']:.1f}° | 下行角度: {next_['angle']:.1f}°"
                    )

    def _validate_text_merging(self, line_info: List[Dict], errors: List[str]):
        """验证文本合并效果，排除水印行"""
        # 只统计非水印行的合并情况
        non_watermark_lines = [line for line in line_info if not line['is_watermark']]

        if not non_watermark_lines:
            return

        merged_lines = sum(1 for line in non_watermark_lines
                           if len(line['words']) >= self.MIN_MERGED_WORDS)
        total_lines = len(non_watermark_lines)

        if merged_lines == 0:
            errors.append(
                f"未检测到合并后的长文本行(单词数≥{self.MIN_MERGED_WORDS})\n"
                f"总行数: {total_lines} | 最长行单词数: "
                f"{max(len(line['words']) for line in non_watermark_lines)}"
            )
        else:
            print(f"\n合并行统计: {merged_lines}/{total_lines} 行达到合并要求(≥{self.MIN_MERGED_WORDS}个单词)")

    def _fail_with_all_errors(self, errors: List[str], line_info: List[Dict]):
        """输出所有错误信息和调试数据"""
        error_msg = ["\n=== 发现以下错误 ==="]
        error_msg.extend(f"❌ {e}" for e in errors)

        # 添加调试信息
        error_msg.append("\n=== 行分组详情 ===")
        error_msg.append(
            "行号 | Y位置 | 高度(px) | 角度 | 水印 | X范围 | 单词数 | 文本样例"
        )
        for line in line_info:
            error_msg.append(
                f"{line['line_num']:3d} | {line['y_min']:3.1f}-{line['y_max']:4.1f}  | {line['height']:7.1f} | "
                f"{line['angle']:5.1f}° | {'✓' if line['is_watermark'] else '✗'} | "
                f"[{line['x_min']:.0f}-{line['x_max']:.0f}] | "
                f"{len(line['words']):4d} | "
                f"{line['text'][:150]}{'...' if len(line['text']) > 150 else ''}"
            )

        self.fail('\n'.join(error_msg))


if __name__ == '__main__':
    unittest.main()
