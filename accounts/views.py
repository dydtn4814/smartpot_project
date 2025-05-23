from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json

RASPI_API_URL =
@csrf_exempt
def kakao_webhook(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        user_message = body.get('userRequest', {}).get('utterance', '')

        # 온도/습도 요청 처리
        if "온도" in user_message or "습도" in user_message:
            try:
                # 라즈베리파이 Flask 서버에서 센서 데이터 요청
                response = requests.get(RASPI_API_URL, timeout=5)
                response.raise_for_status()
                sensor_data = response.json()

                # 예시: 센서 데이터에 온도, 습도 키가 있다고 가정
                # 실제 센서 데이터 포맷에 맞게 수정 필요
                temperature = sensor_data.get("temperature", "알 수 없음")
                humidity = sensor_data.get("humidity", "알 수 없음")

                if "온도" in user_message:
                    reply_text = f"현재 온도는 {temperature}도입니다 🌡️"
                else:
                    reply_text = f"현재 습도는 {humidity}%입니다 💧"

            except requests.RequestException as e:
                reply_text = "센서 데이터를 가져오는 데 실패했어요. 잠시 후 다시 시도해주세요."

            return JsonResponse(make_kakao_response(reply_text))

        # 기존 메시지 처리
        if "온도" in user_message:
            return JsonResponse(make_kakao_response("현재 온도는 25도입니다 🌡️"))
        elif "습도" in user_message:
            return JsonResponse(make_kakao_response("현재 습도는 60%입니다 💧"))
        else:
            return JsonResponse(make_kakao_response("죄송해요, 이해하지 못했어요 😢"))

    return JsonResponse({'error': 'Invalid request method'}, status=405)


    response = requests.post(url, headers=headers, data=data)
    return JsonResponse(response.json(), status=response.status_code)
