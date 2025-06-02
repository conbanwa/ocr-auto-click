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
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string


def ocr_list(file_path):
    url = "http://127.0.0.1:1224/api/ocr"
    b64 = image_to_base64(file_path)
    data = {
        "base64": b64,  # 可选参数示例
        "options": {
            "data.format": "dict",
        }
    }
    headers = {"Content-Type": "application/json"}
    data_str = json.dumps(data)
    response = requests.post(url, data=data_str, headers=headers)
    response.raise_for_status()
    res_dict = json.loads(response.text)
    # info(res_dict)
    # Press Ctrl+F8 to toggle the breakpoint.
    return res_dict


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print(ocr_list('last_screenshot.png'))
