from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json

from .models import SensorData, SoilMoistureThreshold
from django.utils import timezone
from datetime import timedelta




RASPI_TEMP_API_URL = "http://192.168.0.15:5000/sensor/temp" #같은와이파이
RASPI_HUMI_API_URL = "http://192.168.0.15:5000/sensor/humi"
RASPI_SOIL_API_URL = "http://192.168.0.15:5000/sensor/soil"
RASPI_PUMP_API_URL = "http://192.168.0.15:5000/control/pump"


@csrf_exempt
def kakao_webhook(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        user_message = body.get('userRequest', {}).get('utterance', '')

        if "온도" in user_message:
            try:
                response = requests.get(RASPI_TEMP_API_URL, timeout=15)
                response.raise_for_status()
                sensor_data = response.json()

                temperature = sensor_data.get("temperature", "알 수 없음")
                reply_text = f"현재 온도는 🌡{temperature}°C입니다."

            except requests.RequestException:
                reply_text = "센서에서 온도 정보를 가져오지 못했어요 😢"

            return JsonResponse(make_sensor_quickreply_kakao_response(reply_text))

        elif "습도" in user_message:
            try:
                response = requests.get(RASPI_HUMI_API_URL, timeout=15)
                response.raise_for_status()
                sensor_data = response.json()

                humidity = sensor_data.get("humidity", "알 수 없음")
                reply_text = f"현재 습도는 💧{humidity}%입니다."

            except requests.RequestException:
                reply_text = "센서에서 습도 정보를 가져오지 못했어요 😢"

            return JsonResponse(make_sensor_quickreply_kakao_response(reply_text))

        elif "토양 수분" in user_message:
            try:
                response_soil = requests.get(RASPI_SOIL_API_URL, timeout=15) 
                response_soil.raise_for_status()
                soil_data = response_soil.json()

                soil_moisture = soil_data.get("soil_moisture_percentage","알 수 없음")
                reply_text = f"현재 토양 수분은 🌱{soil_moisture}% 입니다."
             
            except requests.RequestException:
                reply_text = "센서에서 토양 수분 정보를 가져오지 못했어요 😢"
                
            return JsonResponse(make_sensor_quickreply_kakao_response(reply_text))

        elif "물 주기" in user_message:
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
        
        elif "동향" in user_message:
            return JsonResponse(make_kakao_response(get_recent_sensor_data()))
         
        elif "기준 토양수분 설정" in user_message:
            
            return JsonResponse(make_kakao_response(get_recent_sensor_data()))
        # 기본 응답
        return JsonResponse(make_kakao_response("온도나 습도를 물어보시면 알려드릴게요 🌡️💧"))
        


    return JsonResponse({'error': 'Invalid request method'}, status=405)


# 온습도 동향 조회 구현
@csrf_exempt 
def receive_sensor_data(request): #라즈베리파이단에서의 데이터 센서값 post요청 받기, db저장
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            temperature = data.get('temperature')
            humidity = data.get('humidity')
            soil_moisture = data.get('soil_moisture')

            if None in (temperature, humidity, soil_moisture):
                return JsonResponse({"status": "error", "message": "데이터 누락"}, status=400)

            # DB에 저장
            SensorData.objects.create(
                temperature=temperature,
                humidity=humidity,
                soil_moisture=soil_moisture
            )
            # 저장 후: 1일 초과된 오래된 데이터 삭제
            deletion_cutoff = timezone.now() - timedelta(days=1)
            SensorData.objects.filter(timestamp__lt=deletion_cutoff).delete()
            return JsonResponse({"status": "success", "message": "데이터 저장 완료"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "fail", "message": "POST 요청만 허용됩니다"}, status=405)


def get_recent_sensor_data(): # 온습도 동향 조회 

    cutoff = timezone.now() - timedelta(hours=1) # 현재시각 기준으로 10분전 데이터들 get
    data_qs = SensorData.objects.filter(timestamp__gte=cutoff).order_by('-timestamp')#최근데이터부터

    # 최근 1일치 데이터 리스트를 JSON으로 변환
    data_list = [
        {   
            "timestamp": d.timestamp.strftime("%Y-%m-%d %H:%M"),
            "temperature": d.temperature,
            "humidity": d.humidity,
            "soil_moisture": d.soil_moisture,
            
        }
        for d in data_qs
    ]
    
    text = conv_dic_to_text(data_list)
      
    return text

def conv_dic_to_text(data): 
  text = ""
  for d in data:
    time = d["timestamp"]
    tem = d["temperature"]
    humi = d["humidity"]
    soil_moisture = d["soil_moisture"]
    text += f"날짜 {time} \n온도:{tem} | 습도:{humi} | 토양수분:{soil_moisture}\n\n"
    
  return text

@csrf_exempt 
def get_setting_values(request):
    if request.method == 'POST':
        if SoilMoistureThreshold.objects.first() == None:
            soil_moi_tres_val = None
        else: 
            soil_moi_tres_val = SoilMoistureThreshold.objects.first().value
        
        # 습도 기준값도 추가하기

        return JsonResponse(
        {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                "simpleText": {
                    "text": f"현재 기준 토양수분값 : {soil_moi_tres_val}%"
                }
            }
            ],
            "quickReplies": [
                    {
                    "label": "🏠처음으로",
                    "action": "block",
                    "blockId": "683941302c50e1482b1ed155", 
                    }, 
                    {
                    "label": "⚙️설정",
                    "action": "block",
                    "blockId": "683d83dcc5b310190b6f79e4", 
                    } 
                    ] 
        
        }
        })

        
    

@csrf_exempt
def set_soil_moisture_threshold(request):
     if request.method == 'POST':
        body = json.loads(request.body)
        user_message = body.get('userRequest', {}).get('utterance', '')
        try:  
            threshold_value = float(user_message)  # 숫자로 변환 시도
        except ValueError:
            return JsonResponse({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": "숫자만 입력 해주세요. (예:28)"
                        }
                    }]
                }
            })

        # 기존 값 삭제하고 저장 (또는 update)
        if(SoilMoistureThreshold.objects.first()==None):
            previous_threshold = 'None'
        else:
            previous_threshold = SoilMoistureThreshold.objects.first().value

        SoilMoistureThreshold.objects.all().delete()
        SoilMoistureThreshold.objects.create(value=threshold_value)

        text = f"기준 토양습도\n🌱{previous_threshold}% 에서\n🌱{threshold_value}% 로 설정되었습니다."
        return JsonResponse(make_kakao_response(text))
        # return JsonResponse(
        #     {
        #     "version": "2.0",
        #     "template": {
        #         "outputs": [
        #             {
        #             "simpleText": {
        #                 "text": f"기준 토양습도 🌱{previous_threshold}% 에서 🌱{threshold_value}%로 설정되었습니다."
        #             }
        #         }
        #         ],
        #         "quickReplies": [
        #               {
        #                 "label": "🏠처음으로",
        #                 "action": "block",
        #                 "blockId": "683941302c50e1482b1ed155", 
        #             },  
        #               ] 
            
        #     }
        #     })





# 설정값을 제공하는 API 뷰 (GET 요청만 허용)
@csrf_exempt 
def get_soil_moisture_threshold(request):
    if request.method == 'GET':
        try:
            # 현재 저장된 토양 습도 임계값 가져오기
            # SoilMoistureThreshold 모델에 최소한 하나의 객체가 있다고 가정
            threshold_obj = SoilMoistureThreshold.objects.first() 
            
            if threshold_obj:
                current_threshold = threshold_obj.value
            else:
                # 설정값이 아직 없을 경우  에러 처리
        
                return JsonResponse({"error": "No soil moisture threshold set yet."}, status=404)
                
            return JsonResponse({
                "status": "success",
                "value": {
                    "soil_moisture_threshold": current_threshold
                }
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"데이터를 가져오는 중 오류 발생: {str(e)}"
            }, status=500)
    else:
        return JsonResponse({"status": "error", "message": "GET 요청만 허용됩니다."}, status=405)



def make_sensor_quickreply_kakao_response(text):
    return {
            "version": "2.0",
            "template": {
                "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
                ],
                "quickReplies": [
                      {
                        "label": "🏠처음으로",
                        "action": "block",
                        "blockId": "683941302c50e1482b1ed155", 
                    },
                      {
                        "label": "💧물 주기",
                        "action": "block",
                        "blockId": "683d4a8047b70d2c1d6921f2",  
                    },
                    {
                        "label": "🌡 온도",
                        "action": "block",
                        "blockId": "68297d9ae7598b00aa7c5474", 
                    },
                    {
                        "label": "💧 습도",
                        "action": "block",
                        "blockId": "68297d9ae7598b00aa7c5474", 
                    },
                    {
                        "label": "🌱 토양 수분",
                        "action": "block",
                        "blockId": "68297d9ae7598b00aa7c5474", 
                    },
                  
                ]
            }
        }


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
                ],
                "quickReplies": [
                    {
                        "label": "🏠처음으로",
                        "action": "block",
                        "blockId": "683941302c50e1482b1ed155", 
                    },
                ]
            }
        }
    
def make_home_quickreply_kakao_response(text):
    return {
            "version": "2.0",
            "template": {
                "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
                ],
                "quickReplies": [
                    {
                        "label": "🏠처음으로",
                        "action": "block",
                        "blockId": "683941302c50e1482b1ed155", 
                    },
                    {
                        "label": "💧물 주기",
                        "action": "block",
                        "blockId": "683d4a8047b70d2c1d6921f2",  
                    }
                ]
            }
        }
    
    