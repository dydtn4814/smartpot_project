from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
RASPI_TEMP_API_URL = "http://192.168.0.15:5000/sensor/temp"
RASPI_SOIL_API_URL = "http://192.168.0.15:5000/sensor/soil"
RASPI_PUMP_API_URL = "http://192.168.0.15:5000/control/pump"

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

        elif "토양 수분" in user_message:
            try:
                response_soil = requests.get(RASPI_SOIL_API_URL, timeout=15) 
                response_soil.raise_for_status()
                soil_data = response_soil.json()

                soil_moisture = soil_data.get("soil_moisture_percentage")
                reply_text = f"현재 토양 수분은 {soil_moisture}% 입니다."
             
            except requests.RequestException:
                reply_text = "센서에서 토양 수분 정보를 가져오지 못했어요."
                
            return JsonResponse(make_kakao_response(reply_text))

        elif "물 줘" in user_message:
            try:
                payload = {}
                
                response_pump = requests.post(RASPI_PUMP_API_URL, json=payload, timeout=15)
                response_pump.raise_for_status()
                pump_response_data = response_pump.json()
                
                if pump_response_data.get("status") == "busy":
                    reply_text = pump_response_data.get("message", "펌프가 이미 작동 중이에요. 잠시 후 다시 시도해주세요.")
                else:
                    duration_sent = pump_response_data.get("duration")
                    reply_text = pump_response_data.get("message", f"{duration_sent}초 동안 물을 주기 시작했어요! 🌱")

            except requests.RequestException:
                reply_text = "펌프에 명령을 보내는 데 실패했어요. 잠시 후 다시 시도해주세요."
            
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

