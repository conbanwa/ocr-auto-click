import requests
import json
import base64


def image_to_base64(file_path):
    """
    Convert an image file to a base64 encoded string

    Args:
        file_path (str): Path to the image file

    Returns:
        str: Base64 encoded string of the image
    """
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def ocr_list(file_path, crop_region=None):
    """
    Perform OCR on an image file with optional crop region

    Args:
        file_path (str): Path to image file
        crop_region (list): [x, y, width, height] of crop region

    Returns:
        dict: OCR results with coordinates adjusted for crop offset
    """
    return _ocr_list_by_base64(image_to_base64(file_path), crop_region)


def _ocr_list_by_base64(b64, crop_region=None):
    """
    Perform OCR on a base64 encoded image with optional crop region

    Args:
        b64 (str): Base64 encoded image
        crop_region (list): [x, y, width, height] of crop region

    Returns:
        dict: OCR results with adjusted coordinates if crop region specified
    """
    url = "http://127.0.0.1:1224/api/ocr"
    data = {
        "base64": b64,
        "options": {
            "data.format": "dict",
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    res_dict = json.loads(response.text)

    # Adjust coordinates if crop region was applied
    if crop_region and 'data' in res_dict:
        crop_x = crop_region[0] if len(crop_region) > 0 and crop_region[0] else 0
        crop_y = crop_region[1] if len(crop_region) > 1 and crop_region[1] else 0

        for item in res_dict['data']:
            if 'box' in item:
                for point in item['box']:
                    point[0] += crop_x
                    point[1] += crop_y

    return res_dict


if __name__ == '__main__':
    # Example usage with crop region
    results = ocr_list('last_screenshot.png', [None, None, 500, 300])
    print(results)
    # print(json.dumps(results, indent=2))
