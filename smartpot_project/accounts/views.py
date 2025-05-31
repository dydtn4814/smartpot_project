from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
RASPI_API_URL = "http://192.168.0.15:5000/sensor"

@csrf_exempt
def kakao_webhook(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        user_message = body.get('userRequest', {}).get('utterance', '')

        if "온도" in user_message:
            try:
                response = requests.get(RASPI_API_URL, timeout=15)
                response.raise_for_status()
                sensor_data = response.json()

                temperature = sensor_data.get("temperature", "알 수 없음")
                reply_text = f"현재 온도는 {temperature}도입니다 🌡️"

            except requests.RequestException:
                reply_text = "센서에서 온도 정보를 가져오지 못했어요 😢"

            return JsonResponse(make_kakao_response(reply_text))

        elif "습도" in user_message:
            try:
                response = requests.get(RASPI_API_URL, timeout=15)
                response.raise_for_status()
                sensor_data = response.json()

                humidity = sensor_data.get("humidity", "알 수 없음")
                reply_text = f"현재 습도는 {humidity}%입니다 💧"

            except requests.RequestException:
                reply_text = "센서에서 습도 정보를 가져오지 못했어요 😢"

            return JsonResponse(make_kakao_response(reply_text))

        # 기본 응답
        return JsonResponse(make_kakao_response("온도나 습도를 물어보시면 알려드릴게요 🌡️💧"))

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def make_kakao_response(text):
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }

