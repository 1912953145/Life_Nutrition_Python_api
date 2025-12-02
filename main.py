# main.py
from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# 强烈建议用环境变量（安全！）
API_KEY = os.getenv("BAIDU_API_KEY", "msKbhkcp4bmOv64lGDQ9mqAJ")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "t3sFAzIQcm4N5li1ViN9RIqCiycP88lY")

# token 缓存
ACCESS_TOKEN = None
EXPIRES_AT = None

def get_access_token():
    global ACCESS_TOKEN, EXPIRES_AT
    if ACCESS_TOKEN and EXPIRES_AT and datetime.now() < EXPIRES_AT:
        return ACCESS_TOKEN

    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    ACCESS_TOKEN = data["access_token"]
    EXPIRES_AT = datetime.now() + timedelta(seconds=data["expires_in"] - 3600)
    return ACCESS_TOKEN

@app.route('/recognize', methods=['POST'])
def recognize():
    if 'image' not in request.files:
        return jsonify({"error": "no image"}), 400

    file = request.files['image']
    img_bytes = file.read()
    if len(img_bytes) > 4*1024*1024:  # 4MB 限制
        return jsonify({"error": "image too large"}), 413

    try:
        token = get_access_token()
        url = f"https://aip.baidubce.com/rest/2.0/image-classify/v2/dish?access_token={token}"

        payload = {
            'image': base64.b64encode(img_bytes).decode('utf-8'),
            'top_num': 3,
            'filter_threshold': '0.1',
            'baike_num': 5
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(url, data=payload, headers=headers)
        r.raise_for_status()
        result = r.json()

        if result.get('result_num', 0) == 0:
            return jsonify({"name": "未识别出菜品", "calorie": 0, "probability": 0})

        food = result['result'][0]
        name = food.get('name', '未知菜品')
        calorie = float(food.get('calorie', 0))
        prob = float(food.get('probability', 0))

        if prob < 0.3:
            name = f"看起来像 {name}，但不确定"

        return jsonify({
            "name": name,
            "calorie": calorie,           # 每100g热量
            "probability": prob
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)