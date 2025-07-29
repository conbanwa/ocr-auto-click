import base64
import json
import math
from enum import Enum
from logging import error, critical
from typing import Dict, List, Optional, Any, TypedDict, Literal

import requests

from auto.config_loader import SERVER_ADDRESS

LINE_TOLERANCE = 10
FONT_HEIGHT_TOLERANCE = 5
ANGLE_TOLERANCE = 5.0  # 角度容差（度）
MAX_CHAR_DISTANCE_RATIO = 1  # 文字块间距超过自身长度1.5倍时不合并


class TextBox(TypedDict):
    """Bounding box coordinates in [x1, y1, x2, y2, x3, y3, x4, y4] format"""
    box: List[tuple[int, int]]
    original_box: List[tuple[int, int]]
    score: float
    similarity: float
    text: str
    center: Optional[List[int]]
    angle: Optional[float]


class OcrResult(TypedDict):
    """Structured OCR result with type hints for all fields"""
    code: Literal[100]  # 100 indicates success
    data: List[TextBox]  # List of detected text boxes
    score: float  # Overall confidence score
    time: float  # Processing time in seconds
    timestamp: str  # ISO format timestamp


# For backward compatibility
OcrDict = OcrResult


# Define enums for OCR parameters
class OcrLanguage(Enum):
    """
    CHINESE = "models/config_chinese.txt"
    ENGLISH = "models/config_en.txt"
    CHINESE_CHT = "models/config_chinese_cht(v2).txt"
    JAPANESE = "models/config_japan.txt"
    KOREAN = "models/config_korean.txt"
    CYRILLIC = "models/config_cyrillic.txt"
    """
    CHINESE = "简体中文"
    ENGLISH = "English"
    CHINESE_CHT = "繁體中文"
    JAPANESE = "日本語"
    KOREAN = "한국어"
    RUSSIAN = "Русский"


class OcrLimitSideLen(Enum):
    DEFAULT = 1024
    MEDIUM = 2048
    HIGH = 4096
    NO_LIMIT = 999999


class TbpuParser(Enum):
    MULTI_PARA = "multi_para"
    MULTI_LINE = "multi_line"
    MULTI_NONE = "multi_none"
    SINGLE_PARA = "single_para"
    SINGLE_LINE = "single_line"
    SINGLE_NONE = "single_none"
    SINGLE_CODE = "single_code"
    NONE = "none"
    BY_LINE = "by_line"  # 行分组（不考虑字体）
    BY_FONT = "by_font"  # 新增：按行和字体分组


class DataFormat(Enum):
    DICT = "dict"
    TEXT = "text"


def extract_words(result: Optional[OcrDict]) -> List[str]:
    """从OCR结果中提取所有单词(辅助方法)"""
    if not result or 'data' not in result:
        error(f"'data' not in result: {result}")
        return []
    words = []
    for item in result['data']:
        words.extend(item['text'].split())
    return words


def image_to_base64(file_path: str) -> str:
    """
    Convert an image file to a base64 encoded string

    Args:
        file_path (str): Path to the image file

    Returns:
        str: Base64 encoded string of the image
    """
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _dict_to_ocr_result(data: Dict[str, Any]) -> Optional[OcrResult]:
    """
    Convert a dictionary to an OcrResult object
    
    Args:
        data: Dictionary containing OCR result data
        
    Returns:
        OcrResult: Parsed OCR result or None if data is invalid
    """
    if not data or 'code' not in data or data.get('code') != 100:
        error(f"Invalid OCR result data: {data}")
        return None

    try:
        # Extract basic fields
        result: OcrResult = {
            'code': data['code'],
            'data': [],
            'score': data.get('score', 0.0),
            'time': data.get('time', 0.0),
            'timestamp': data.get('timestamp', '')
        }

        # Convert each text box
        for item in data.get('data', []):
            if 'box' not in item or 'text' not in item:
                continue

            text_box: TextBox = {
                'box': [tuple(point) for point in item['box']],
                'original_box': [tuple(point) for point in item.get('original_box', item['box'])],
                'score': float(item.get('score', 0.0)),
                'similarity': float(item.get('similarity', 0.0)),
                'text': str(item['text']),
                'center': list(item['center']) if 'center' in item and item['center'] is not None else None,
                'angle': float(item['angle']) if 'angle' in item and item['angle'] is not None else None
            }
            result['data'].append(text_box)

        return result

    except Exception as e:
        error(f"Error converting OCR result: {e}")
        return None


def ocr_list(
        file_path: str = '../src/last_screenshot.png',
        crop_region: Optional[List[Optional[int]]] = None,
        ocr_language: OcrLanguage = OcrLanguage.CHINESE,
        ocr_cls: bool = False,
        ocr_limit_side_len: OcrLimitSideLen = OcrLimitSideLen.HIGH,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        tbpu_ignore_area: Optional[List[List[int]]] = None,
        data_format: DataFormat = DataFormat.DICT
) -> Optional[OcrDict]:
    dict_value = ocr_list_by_base64(image_to_base64(file_path), crop_region, ocr_language, ocr_cls, ocr_limit_side_len,
                                    tbpu_parser, tbpu_ignore_area, data_format)
    return _dict_to_ocr_result(dict_value)


def ocr_list_by_base64(
        base64code: str,
        crop_region: Optional[List[Optional[int]]] = None,
        ocr_language: OcrLanguage = OcrLanguage.CHINESE,
        ocr_cls: bool = False,
        ocr_limit_side_len: OcrLimitSideLen = OcrLimitSideLen.HIGH,
        tbpu_parser: TbpuParser = TbpuParser.NONE,
        tbpu_ignore_area: Optional[List[List[int]]] = None,
        data_format: DataFormat = DataFormat.DICT
) -> Optional[Dict[str, Any]]:
    """
    Perform OCR on a base64 encoded image with optional crop region and configurable options
    url = "http://127.0.0.1:1224/api/ocr/get_options"

    Args:
        base64code (str): Base64 encoded image
        crop_region (list): [x, y, width, height] of crop region
        ocr_language (OcrLanguage): Language/model configuration
        ocr_cls (bool): Enable text direction correction
        ocr_limit_side_len (OcrLimitSideLen): Maximum image side length
        tbpu_parser (TbpuParser): Text block parsing scheme
        tbpu_ignore_area (list): List of ignore areas [[left_top_x,y],[right_bottom_x,y]]
        data_format (DataFormat): Output data format

    Returns:
        dict: OCR results with adjusted coordinates if crop region specified
    """
    url = f"http://{SERVER_ADDRESS}/api/ocr"
    data = {
        "base64": base64code,
        "options": {
            "ocr.language": ocr_language.value,
            "ocr.cls": ocr_cls,
            "ocr.limit_side_len": ocr_limit_side_len.value,
            "tbpu.parser": tbpu_parser.value,
            "data.format": data_format.value,
            "tbpu.ignoreArea": tbpu_ignore_area or []
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    res_dict = json.loads(response.text)

    # Adjust coordinates if crop region was applied
    if crop_region and 'data' in res_dict:
        crop_x = crop_region[0] or 0
        crop_y = crop_region[1] or 0

        for item in res_dict['data']:
            if 'box' in item:
                for point in item['box']:
                    point[0] += crop_x
                    point[1] += crop_y

    # 在分组前计算原始文本块的角度
    if 'data' in res_dict:
        for item in res_dict['data']:
            if 'box' in item and len(item['box']) == 4:
                # 计算原始角度
                item['angle'] = _calculate_angle(item['box'])
                # 保存原始边界框（用于分组）
                item['original_box'] = item['box']
                # 计算中心点
                item['center'] = _calculate_center(item['box'])

    # 行分组处理
    if res_dict.get('code') == 100 and data_format == DataFormat.DICT:
        if tbpu_parser == TbpuParser.BY_LINE:
            res_dict['data'] = _group_by_line(res_dict['data'])
        elif tbpu_parser == TbpuParser.BY_FONT:
            res_dict['data'] = _group_by_font(res_dict['data'])

        # 确保所有项都有必要的字段
        if 'data' in res_dict:
            if type(res_dict['data']) is str:
                error(f"{res_dict['data']} is str")
                return None
            for item in res_dict['data']:
                # 确保所有项都有必要的字段
                if 'score' not in item:
                    error(f"no score attribute in {item}")
                    # item['score'] = 1.0
                if 'center' not in item:
                    error(f"no center attribute in {item}")
                    # item['center'] = _calculate_center(item.get('box', [[0, 0], [0, 0], [0, 0], [0, 0]]))
                if 'angle' not in item:
                    error(f"no angle attribute in {item}")
                    # item['angle'] = 0.0
    else:
        error(f"code {res_dict} ==== {res_dict}")
    return res_dict


def _calculate_angle(box: List[List[float]]) -> float:
    """Calculate text tilt angle from bounding box"""
    if len(box) != 4:
        return 0.0

    # 找到底部两个点（y值最大的两个点）
    sorted_points = sorted(box, key=lambda p: p[1], reverse=True)
    bottom_points = sorted_points[:2]

    # 确定左右顺序
    if bottom_points[0][0] < bottom_points[1][0]:
        left_bottom = bottom_points[0]
        right_bottom = bottom_points[1]
    else:
        left_bottom = bottom_points[1]
        right_bottom = bottom_points[0]

    # 计算水平和垂直差异
    dx = right_bottom[0] - left_bottom[0]
    dy = right_bottom[1] - left_bottom[1]

    # 避免除以零
    if dx == 0:
        return 90.0 if dy > 0 else -90.0

    # 计算弧度角度并转换为度
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # 将角度标准化到-45到45度范围内
    if angle_deg > 45:
        angle_deg -= 180
    elif angle_deg < -45:
        angle_deg += 180

    return round(angle_deg, 2)


def _calculate_center(box: List[List[int]]) -> List[int]:
    """Calculate center point from bounding box"""
    if len(box) != 4:
        return [0, 0]

    xs = [p[0] for p in box]
    center_x: int = int(sum(xs) / 4)

    ys = [p[1] for p in box]
    center_y: int = int(sum(ys) / 4)
    if type(center_x) is not int or type(center_y) is not int:
        critical(f"center_x: {center_x}, center_y: {center_y}")
    return [center_x, center_y]


def _group_text_lines(
        data: List[TextBox],
        tolerance: int = LINE_TOLERANCE,
        per_font: bool = False,
        angle_tolerance: float = ANGLE_TOLERANCE
) -> List[TextBox]:
    """
    通用文本行分组函数，考虑角度差异和文字块间距

    Args:
        data: OCR结果数据
        tolerance: 行分组容差(像素)
        per_font: 是否按字体分组
        angle_tolerance: 角度容差(度)

    Returns:
        分组后的行列表
    """
    # 计算每个文本项的特征
    items = []
    for item in data:
        # 检查是否有必要的字段
        if 'original_box' not in item or len(item.get('original_box', [])) != 4:
            continue
        if 'angle' not in item:
            continue

        # 使用原始边界框计算特征（分组前）
        _box = item['original_box']
        center_x, center_y = _calculate_center(_box)
        xs = [p[0] for p in _box]
        ys = [p[1] for p in _box]
        min_x, min_y = min(xs), min(ys)
        max_x, max_y = max(xs), max(ys)
        # center_x = int((min_x + max_x) / 2)
        # center_y = int((min_y + max_y) / 2)
        font_height = max_y - min_y

        # 计算特征
        features = {
            "text": item.get('text', ''),
            "score": item.get('score', 1.0),
            "box": _box,  # 使用原始边界框
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "center_x": center_x,
            "center_y": center_y,
            "font_height": font_height,
            "angle": item['angle']  # 使用原始角度
        }

        items.append(features)

    # 按y坐标排序
    items.sort(key=lambda x: x['center_y'])

    # 分组文本项
    groups = []
    for item in items:
        matched = False
        for group in groups:
            # 计算文字块间距
            distance = item['min_x'] - group['max_x']
            char_width = (group['max_x'] - group['min_x'])
            max_char_distance = char_width * MAX_CHAR_DISTANCE_RATIO

            # 如果间距过大则跳过合并
            if distance > max_char_distance:
                continue

            # 检查是否匹配
            y_match = abs(item['center_y'] - group['center_y']) <= tolerance

            # 检查边界框是否重叠
            y_overlap = not (item['min_y'] > group['max_y'] or item['max_y'] < group['min_y'])

            # 检查字体高度是否匹配
            font_match = True
            if per_font:
                font_match = abs(item['font_height'] - group['font_height']) <= FONT_HEIGHT_TOLERANCE

            # 检查角度是否匹配
            angle_match = abs(item['angle'] - group['angle']) <= angle_tolerance

            if y_match and y_overlap and font_match and angle_match:
                # 更新组的边界
                group['min_x'] = min(group['min_x'], item['min_x'])
                group['max_x'] = max(group['max_x'], item['max_x'])
                group['min_y'] = min(group['min_y'], item['min_y'])
                group['max_y'] = max(group['max_y'], item['max_y'])

                # 更新中心点
                group['center_x'] = int((group['min_x'] + group['max_x']) / 2)
                group['center_y'] = int((group['min_y'] + group['max_y']) / 2)

                # 更新字体高度
                if per_font:
                    group['font_height'] = max(group['font_height'], item['font_height'])

                # 更新角度为平均值
                group['angle'] = (group['angle'] * len(group['items']) + item['angle']) / (len(group['items']) + 1)

                # 添加项目到组
                group['items'].append(item)
                matched = True
                break

        if not matched:
            new_group = {
                "items": [item],
                "min_x": item['min_x'],
                "max_x": item['max_x'],
                "min_y": item['min_y'],
                "max_y": item['max_y'],
                "center_x": item['center_x'],
                "center_y": item['center_y'],
                "font_height": item['font_height'],
                "angle": item['angle']  # 初始角度
            }
            groups.append(new_group)

    # 构建行结果
    lines = []
    for group in groups:
        if not group['items']:
            continue

        # 按x坐标排序
        sorted_items = sorted(group['items'], key=lambda x: x['min_x'])

        # 合并文本
        line_text = ' '.join(item['text'] for item in sorted_items)

        # 计算平均置信度
        avg_score = sum(item['score'] for item in sorted_items) / len(sorted_items)

        # 计算边界框
        min_x = min(item['min_x'] for item in sorted_items)
        max_x = max(item['max_x'] for item in sorted_items)
        min_y = min(item['min_y'] for item in sorted_items)
        max_y = max(item['max_y'] for item in sorted_items)

        # 创建行对象
        _box = [
            [min_x, min_y],
            [max_x, min_y],
            [max_x, max_y],
            [min_x, max_y]
        ]

        _line = {
            "text": line_text,
            "score": avg_score,
            "box": _box,
            "center": [group['center_x'], group['center_y']],
            "angle": group['angle']  # 使用组平均角度
        }

        # 如果按字体分组，添加字体高度
        if per_font:
            _line["font_height"] = group['font_height']

        lines.append(_line)

    # 按y坐标排序行
    lines.sort(key=lambda x: x['center'][1])
    return lines


def _group_by_line(
        data: List[TextBox],
        tolerance: int = LINE_TOLERANCE
) -> List[TextBox]:
    """按y坐标分组文本行（不考虑字体）"""
    return _group_text_lines(data, tolerance, per_font=False)


def _group_by_font(
        data: List[TextBox],
        tolerance: int = LINE_TOLERANCE
) -> List[TextBox]:
    """按y坐标和字体大小分组文本行"""
    return _group_text_lines(
        data,
        tolerance,
        per_font=True
    )


if __name__ == '__main__':
    # 使用行分组解析器的示例
    results = ocr_list(
        file_path='../src/test_screenshot.png',
        # crop_region=[100, 100, 800, 600],
        ocr_language=OcrLanguage.CHINESE,
        tbpu_parser=TbpuParser.BY_LINE,  # 使用行分组解析器
        data_format=DataFormat.DICT,
        ocr_cls=False
    )

    # 打印分组后的结果
    for i, line in enumerate(results.get('data', [])):
        print(f"行 {i + 1} (Y={line['center'][1]:.1f}, 角度={line['angle']:.2f}°): {line['text']}")
        # print(f"边界框: {line['box']}  置信度: {line.get('score', 'N/A')}")
