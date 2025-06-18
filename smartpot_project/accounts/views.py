from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
import urllib.parse
from django.views.decorators.csrf import csrf_exempt
import requests
import json

from .models import SensorData, SoilMoistureThreshold, HumidityThreshold
from django.utils import timezone
from datetime import timedelta




RASPI_TEMP_API_URL = "http://192.168.0.15:5000/sensor/temp" #같은와이파이
RASPI_HUMI_API_URL = "http://192.168.0.15:5000/sensor/humi"
RASPI_SOIL_API_URL = "http://192.168.0.15:5000/sensor/soil"
RASPI_PUMP_API_URL = "http://192.168.0.15:5000/control/pump"
RASPI_LED_API_URL = "http://192.168.0.15:5000/control/led"
RASPI_HUMIDIFIER_API_URL = "http://192.168.0.15:5000/control/humidifier"
RASPI_FAN_API_URL = "http://192.168.0.15:5000/control/fan"

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
                
                response_pump = requests.post(RASPI_PUMP_API_URL, timeout=15)
                response_pump.raise_for_status()
                pump_response_data = response_pump.json()
                
                if pump_response_data.get("status") == "busy":
                    reply_text = pump_response_data.get("message", "펌프가 이미 작동 중이에요. 잠시 후 다시 시도해주세요.")
                else:
                    reply_text = (f" 물 주기 완료! 💧")

            except requests.RequestException:
                reply_text = "펌프에 명령을 보내는 데 실패했어요. 잠시 후 다시 시도해주세요."
            
            return JsonResponse(make_kakao_response(reply_text))
        elif "LED" in user_message:
            try:
                payload = {}
                
                response_led = requests.post(RASPI_LED_API_URL, json=payload, timeout=15)
                response_led.raise_for_status()
                # led_response_data = response_led.json()
                
            except requests.RequestException:
                reply_text = "LED에 명령을 보내는 데 실패했어요. 잠시 후 다시 시도해주세요."
            
            return JsonResponse(make_kakao_response(reply_text))
        
        elif "가습기" in user_message:
            try:
                payload = {}
                
                response_humidfier = requests.post(RASPI_HUMIDIFIER_API_URL, timeout=15)
                response_humidfier.raise_for_status()
                humidfier_response_data = response_humidfier.json()
                
                if humidfier_response_data.get("status") == "busy":
                    reply_text = humidfier_response_data.get("message", "가습가 이미 작동 중이에요. 잠시 후 다시 시도해주세요.")
                else:
                    reply_text = (f" 가습기 작동 완료! 💧")

            except requests.RequestException:
                reply_text = "가습기에 명령을 보내는 데 실패했어요. 잠시 후 다시 시도해주세요."
            
            return JsonResponse(make_kakao_response(reply_text))
        
        elif "팬 작동" in user_message:
            try:
                payload = {}
                
                response_pump = requests.post(RASPI_FAN_API_URL, timeout=15)
                response_pump.raise_for_status()
                pump_response_data = response_pump.json()
                
                if pump_response_data.get("status") == "busy":
                    reply_text = pump_response_data.get("message", "팬이 이미 작동 중이에요. 잠시 후 다시 시도해주세요.")
                else:
                    reply_text = (f" 팬 작동 완료! 💧")

            except requests.RequestException:
                reply_text = "팬에 명령을 보내는 데 실패했어요. 잠시 후 다시 시도해주세요."
            
            return JsonResponse(make_kakao_response(reply_text))
        
        elif "동향" in user_message:
            return JsonResponse(make_kakao_response(_get_recent_sensor_data()))
    
        # 기본 응답
        return JsonResponse(make_kakao_response("온도나 습도를 물어보시면 알려드릴게요 🌡️💧"))
        


    return JsonResponse({'error': 'Invalid request method'}, status=405)



@csrf_exempt 
def receive_sensor_data(request): #라즈베리파이단 서버 측에서 보낸 센서 값들 받는 함수 + db저장
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


def _get_recent_sensor_data(): # 온습도 동향 조회 

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
    
    text = _conv_dic_to_text(data_list)
      
    return text

def _conv_dic_to_text(data): 
  text = ""
  for d in data:
    time = d["timestamp"]
    tem = d["temperature"]
    humi = d["humidity"]
    soil_moisture = d["soil_moisture"]
    text += f"날짜 {time} \n온도:{tem} | 습도:{humi} | 토양수분:{soil_moisture}\n\n"
    
  return text

@csrf_exempt 
def get_setting_values(request): # 현재 기준 설정값 조회 뷰
    if request.method == 'POST':
        if SoilMoistureThreshold.objects.first() == None:
            soil_moi_tres_val = None
        else: 
            soil_moi_tres_val = SoilMoistureThreshold.objects.first().value
            
        if HumidityThreshold.objects.first() == None:
            humi_tres_val = None
        else: 
            humi_tres_val = HumidityThreshold.objects.first().value

        # 습도 기준값도 추가하기

        return JsonResponse(
        {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                "simpleText": {
                    "text": f"🌱현재 기준 토양수분 값 : {soil_moi_tres_val}%\n💧현재 기준 습도 : {humi_tres_val}% "
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


 # 라즈베리파이 서버로 토양수분기준값 주는 함수
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

# 라즈베리파이 서버로 습도기준값 주는 함수
@csrf_exempt 
def get_humidity_threshold(request):
    if request.method == 'GET':
        try:
            threshold_obj = HumidityThreshold.objects.first() 
            
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
       
# receive_number() 으로 받은 값 db저장
def _store_soil_moisture_threshold(threshold_value):

    # 기존 값 삭제하고 저장 (또는 update)
    if(SoilMoistureThreshold.objects.first()==None):
        previous_threshold = 'None'
    else:
        previous_threshold = SoilMoistureThreshold.objects.first().value

    SoilMoistureThreshold.objects.all().delete()
    SoilMoistureThreshold.objects.create(value=threshold_value)

    text = f"기준 토양습도\n🌱{previous_threshold}% 에서\n🌱{threshold_value}% 로 설정되었습니다."
    return text

# receive_number() 으로 받은 값 db저장    
def _store_humidity_threshold(threshold_value):

    # 기존 값 삭제하고 저장 (또는 update)
    if(HumidityThreshold.objects.first()==None):
        previous_threshold = 'None'
    else:
        previous_threshold = HumidityThreshold.objects.first().value

    HumidityThreshold.objects.all().delete()
    HumidityThreshold.objects.create(value=threshold_value)

    text = f"기준 습도\n💧{previous_threshold}% 에서\n💧{threshold_value}% 로 설정되었습니다."
    return text
        
@csrf_exempt 
def receive_number(request): # 사용자에게서 카카오톡을 통해 설정 값 받는 함수 
    if request.method == 'POST':
        body = json.loads(request.body)
        setting_val = body.get('userRequest', {}).get('utterance', '')
        context = body.get('contexts',[{}])[0].get('name',' ')
        
        try:
            setting_val = float(setting_val)
        except ValueError:
            reply_text = "❗설정값 오류❗"
            return JsonResponse(make_setting_quickreply_kakao_response(reply_text))
        
        if setting_val <= 0 or setting_val > 100:
            reply_text = "❗설정값 오류❗"
            return JsonResponse(make_setting_quickreply_kakao_response(reply_text))
        # 오류메세지 작동 잘 안됨 챗봇 한계인듯?
        
        # print(body)
        # print(setting_val)
        # print(context)
        
        if context == "context_soil_moi": # 토양수분 설정 분기에서 왔으면
            text = _store_soil_moisture_threshold(setting_val) # 기준토양수분 update
        elif context == "context_humi": # 습도 설정 분기에서 왔으면
            text = _store_humidity_threshold(setting_val)   # 기준 습도 update
        
        return JsonResponse(make_kakao_response(text))
    
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
    
def make_setting_quickreply_kakao_response(text):
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
                        "label": "⚙️설정",
                        "action": "block",
                        "blockId": "68289cdcd9c3e21ccc37740c",  
                    }
                ]
            }
        }