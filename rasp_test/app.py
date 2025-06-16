from flask import Flask, jsonify, request # request 임포트
import threading
import time
import requests
import board
import adafruit_dht
import smbus
import digitalio
import json
from db import init_db, save_setting

# --- 네오픽셀 라이브러리 ---
import neopixel

app = Flask(__name__)

POST_SENSOR_DATAS_URL = "http://192.168.0.34:8000/sensor/receive/"  #네트워크 바꾸고 , 장고서버 열떄 python manage.py runserver 0.0.0.0:8000

GET_SOIL_MOISTURE_THRESHOLD_URL = "http://192.168.0.34:8000/soil_moisture_threshold/"
GET_HUMIDITY_THRESHOLD_URL = "http://192.168.0.34:8000/humidity_threshold/"

#온습도 센서 설정
TEM_HUMI_SENSOR_PIN = board.D23

try:
    dhtDevice = adafruit_dht.DHT11(TEM_HUMI_SENSOR_PIN)
except Exception as e:
    print(f"센서 초기화 실패: {e}")
    dhtDevice = None

# 토양 수분 센서 설정 (I2C 설정)
address = 0X48
A0 = 0X40
I2C_BUS = 1

try:
    bus = smbus.SMBus(I2C_BUS)
except FileNotFoundError:
    print(f"I2C 버스 {I2C_BUS}를 찾을 수 없습니다.")
    bus = None
except Exception as e:
    print(f"SMBus 초기화 중 오류 발생: {e}")
    bus = None

# 워터 펌프 릴레이 핀 설정
PUMP_PIN_NUMBER = board.D17
pump_pin = None
PUMP_OFF_STATE = True  # Active-LOW  HIGH가 꺼짐
PUMP_ON_STATE = False  # Active-LOW  LOW가 켜짐
try:
    pump_pin = digitalio.DigitalInOut(PUMP_PIN_NUMBER)
    pump_pin.direction = digitalio.Direction.OUTPUT
    pump_pin.value = PUMP_OFF_STATE
    print(f"펌프 핀 (GPIO{PUMP_PIN_NUMBER.id}) 초기화 완료. 현재 상태: OFF")
except Exception as e:
    print(f"펌프 핀 초기화 실패: {e}")

pump_is_busy = False
pump_lock = threading.Lock()
duration_seconds = 3

# 가습기 모듈 핀 설정
HUMIDIFIER_PIN_NUMBER = board.D24
humidifier_pin = None
try:
    humidifier_pin = digitalio.DigitalInOut(HUMIDIFIER_PIN_NUMBER)
    humidifier_pin.direction = digitalio.Direction.OUTPUT
    humidifier_pin.value = False
    print(f"가습기 핀 (GPIO{HUMIDIFIER_PIN_NUMBER.id}) 초기화 완료.")
except Exception as e:
    print(f"가습기 핀 초기화 실패: {e}")

humidifier_is_busy = False
humidifier_lock = threading.Lock()
FIXED_HUMIDIFIER_DURATION_SECONDS = 3

# 네오픽셀 LED 설정
NEOPIXEL_PIN = board.D18
NUM_PIXELS = 16
DEFAULT_BRIGHTNESS = 0.5
DEFAULT_COLOR = (255, 255, 255)
pixels = None
try:
    pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, auto_write=False)
    pixels.fill((0, 0, 0)); pixels.show()
    print("네오픽셀 초기화 완료.")
except Exception as e:
    print(f"네오픽셀 초기화 실패: {e}")

# ===== 자동 제어를 위한 전역 변수 추가 =====
current_soil_moisture_threshold = None
current_humidity_threshold = None
last_auto_pump_time = 0
last_auto_humidifier_time = 0
AUTO_CONTROL_COOLDOWN = 300  # 5분 쿨다운 (같은 장치 연속 작동 방지)

# 헬퍼 함수: 일정 시간 펌프 작동 후 끄기 (스레드에서 실행)
def _operate_pump_for_duration():
    global pump_is_busy 
    
    if pump_pin is None:
        print("오류: 펌프 핀이 초기화되지 않아 작동할 수 없습니다.")
        with pump_lock: 
            pump_is_busy = False
        return

    print(f"{duration_seconds}초 동안 펌프 작동을 시작합니다.")
    try:
        pump_pin.value = PUMP_ON_STATE
        print("펌프 ON")
        
        time.sleep(duration_seconds)
        
        pump_pin.value = PUMP_OFF_STATE
        print("펌프 OFF")
        
    except Exception as e:
        print(f"펌프 작동 중 오류 발생: {e}")
        if pump_pin:
            pump_pin.value = PUMP_OFF_STATE
            print("오류 발생으로 펌프 강제 OFF")
    finally:
        with pump_lock:
            pump_is_busy = False
        print("펌프 작동 완료, 플래그 해제.")
        return 1

# 헬퍼 함수: 일정 시간 가습기 작동
def _operate_humidifier_for_duration():
    global humidifier_is_busy
    
    if humidifier_pin is None:
        print("오류: 가습기 핀이 초기화되지 않아 작동할 수 없습니다.")
        with humidifier_lock:
            humidifier_is_busy = False
        return

    print(f"{FIXED_HUMIDIFIER_DURATION_SECONDS}초 동안 가습기 작동을 시작합니다.")
    try:
        humidifier_pin.value = True
        print("가습기 ON")
        
        time.sleep(FIXED_HUMIDIFIER_DURATION_SECONDS)
        
        humidifier_pin.value = False
        print("가습기 OFF")
        
    except Exception as e:
        print(f"가습기 작동 중 오류 발생: {e}")
        if humidifier_pin:
            humidifier_pin.value = False
            print("오류 발생으로 가습기 강제 OFF")
    finally:
        with humidifier_lock:
            humidifier_is_busy = False
        print("가습기 작동 완료, 플래그 해제.")
        return 1

# ===== 자동 제어 함수들 추가 =====
def auto_pump_control(current_soil_moisture):
    """토양 수분이 임계값보다 낮으면 자동으로 펌프 작동"""
    global last_auto_pump_time, pump_is_busy
    
    if current_soil_moisture_threshold is None:
        return
    
    current_time = time.time()
    
    # 토양 수분이 임계값보다 낮고, 쿨다운 시간이 지났으며, 펌프가 작동중이지 않을 때
    if (current_soil_moisture < current_soil_moisture_threshold and 
        current_time - last_auto_pump_time > AUTO_CONTROL_COOLDOWN and 
        not pump_is_busy):
        
        print(f"🚨 자동 급수 작동! 현재 토양수분: {current_soil_moisture}%, 임계값: {current_soil_moisture_threshold}%")
        
        with pump_lock:
            if not pump_is_busy:
                pump_is_busy = True
                last_auto_pump_time = current_time
                
                # 백그라운드에서 펌프 작동
                pump_thread = threading.Thread(target=_operate_pump_for_duration)
                pump_thread.daemon = True
                pump_thread.start()

def auto_humidifier_control(current_humidity):
    """습도가 임계값보다 낮으면 자동으로 가습기 작동"""
    global last_auto_humidifier_time, humidifier_is_busy
    
    if current_humidity_threshold is None:
        return
    
    current_time = time.time()
    
    # 습도가 임계값보다 낮고, 쿨다운 시간이 지났으며, 가습기가 작동중이지 않을 때
    if (current_humidity < current_humidity_threshold and 
        current_time - last_auto_humidifier_time > AUTO_CONTROL_COOLDOWN and 
        not humidifier_is_busy):
        
        print(f"🚨 자동 가습기 작동! 현재 습도: {current_humidity}%, 임계값: {current_humidity_threshold}%")
        
        with humidifier_lock:
            if not humidifier_is_busy:
                humidifier_is_busy = True
                last_auto_humidifier_time = current_time
                
                # 백그라운드에서 가습기 작동
                humidifier_thread = threading.Thread(target=_operate_humidifier_for_duration)
                humidifier_thread.daemon = True
                humidifier_thread.start()

# 워터 펌프 요청 처리 함수
@app.route('/control/pump', methods=['POST'])
def timed_pump_control():
    global pump_is_busy 

    if pump_pin is None:
        return jsonify({"error": "펌프 핀이 초기화되지 않았습니다."}), 500

    with pump_lock:
        if pump_is_busy:
            print("펌프가 이미 작동 중입니다. 새로운 요청을 무시합니다.")
            return jsonify({"status": "busy", "message": "펌프가 이미 작동 중입니다. 잠시 후 시도해주세요."}), 429 
        pump_is_busy = True 

    if _operate_pump_for_duration() == 1:
        message = "worked!"
    
    return jsonify({"status": "success", "message": message, "pump_state": "on", "duration": duration_seconds})

# 가습기 제어 API 엔드포인트
@app.route('/control/humidifier', methods=['POST'])
def timed_humidifier_control():
    global humidifier_is_busy

    if humidifier_pin is None:
        return jsonify({"error": "가습기 핀이 초기화되지 않았습니다."}), 500

    with humidifier_lock:
        if humidifier_is_busy:
            print("가습기가 이미 작동 중입니다. 새로운 요청을 무시합니다.")
            return jsonify({"status": "busy", "message": "가습기가 이미 작동 중입니다. 잠시 후 시도해주세요."}), 429
        humidifier_is_busy = True

    if _operate_humidifier_for_duration() == 1:
        message = "worked!"

    return jsonify({"status": "success", "message": message, "humidifier_state": "on", "duration": FIXED_HUMIDIFIER_DURATION_SECONDS})

# LED 제어 API 엔드포인트
@app.route('/control/led', methods=['POST'])
def control_led():
    if pixels is None:
        return jsonify({"error": "네오픽셀이 초기화되지 않았습니다."}), 500
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "요청 본문이 비어있습니다."}), 400
        
        state = data.get('state')

        if state == 'on':
            pixels.brightness = DEFAULT_BRIGHTNESS
            pixels.fill(DEFAULT_COLOR)
            pixels.show()
            message = "네오픽셀 LED를 켰습니다."

        elif state == 'off':
            pixels.fill((0, 0, 0))
            pixels.show()
            message = "네오픽셀 LED를 껐습니다."
            
        else:
            return jsonify({"error": "잘못된 state 값입니다. 'on' 또는 'off'를 사용하세요."}), 400
        
        print(message)
        return jsonify({"status": "success", "message": message})

    except Exception as e:
        error_message = f"LED 제어 중 오류 발생: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500    

@app.route('/sensor/humi', methods=['GET'])
@app.route('/sensor/temp', methods=['GET'])
def get_tem_humi_data():
    if dhtDevice is None:
        return jsonify({"error": "Sensor not initialized"}), 500
        
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        if temperature_c is not None and humidity is not None:
            print(f"측정 성공: Temp={temperature_c:.1f}C, Humidity={humidity}%")
            
            return jsonify({
                "temperature": temperature_c,
                "humidity": humidity
            })
        else:
            return jsonify({"error": "Failed to retrieve data from sensor. Please try again."}), 500

    except RuntimeError as error:
        print(f"센서 읽기 오류: {error.args[0]}")
        return jsonify({"error": str(error)}), 500
    
    except Exception as e:
        print(f"예외 발생: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500


@app.route('/sensor/soil', methods=['GET'])
def get_soil_moisture_data():
    if bus is None:
        return jsonify({"error": "I2C 버스 초기화 실패"}), 500
        
    try:
        bus.write_byte(address, A0)
        bus.read_byte(address)
        soil_moisture_value = bus.read_byte(address)

        min_moisture_raw = 20 
        max_moisture_raw = 220  
        
        moisture_raw_value = max(min_moisture_raw, min(soil_moisture_value, max_moisture_raw))

        if max_moisture_raw == min_moisture_raw:
             soil_moisture_percentage = 0
        else:
             soil_moisture_percentage = 100 * ( (moisture_raw_value - min_moisture_raw) / (max_moisture_raw - min_moisture_raw))

        soil_moisture_percentage = round(soil_moisture_percentage, 1)

        print(f"토양 수분 측정 성공: Raw={soil_moisture_value}, Percentage={soil_moisture_percentage}%")
        return jsonify({
            "soil_moisture_percentage": soil_moisture_percentage
        })

    except IOError as e:
        print(f"I/O 오류 발생 (PCF8591): {e}")
        return jsonify({"error": f"PCF8591 통신 오류: {e}"}), 500
    except Exception as e:
        print(f"토양 수분 센서 예외 발생: {e}")
        return jsonify({"error": f"토양 수분 센서 처리 중 예외 발생: {e}"}), 500


def _read_tem_humi_data():
    if dhtDevice is None:
        print("error: Sensor not initialized")
        return None
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        if temperature_c is not None and humidity is not None:
            print(f"측정 성공: Temp={temperature_c:.1f}C, Humidity={humidity}%")
            return {
                "temperature": temperature_c,
                "humidity": humidity
            }
        else:
            print("error: Failed to retrieve data from sensor.")
            return None

    except RuntimeError as error:
        print(f"센서 읽기 오류: {error.args[0]}")
        return None
    
    except Exception as e:
        print(f"예외 발생: {e}")
        return None
    
def _read_soil_moisture_data():
    if bus is None:
        print("error: I2C 버스 초기화 실패")
        return None
        
    try:
        bus.write_byte(address, A0)
        bus.read_byte(address)
        soil_moisture_value = bus.read_byte(address)

        min_moisture_raw = 20 
        max_moisture_raw = 220  
        
        moisture_raw_value = max(min_moisture_raw, min(soil_moisture_value, max_moisture_raw))

        if max_moisture_raw == min_moisture_raw:
             soil_moisture_percentage = 0
        else:
             soil_moisture_percentage = 100 * ((moisture_raw_value - min_moisture_raw) / (max_moisture_raw - min_moisture_raw))

        soil_moisture_percentage = round(soil_moisture_percentage, 1)

        print(f"토양 수분 측정 성공: Raw={soil_moisture_value}, Percentage={soil_moisture_percentage}%")
        return {
            "soil_moisture": soil_moisture_percentage
        }

    except IOError as e:
        print(f"I/O 오류 발생 (PCF8591): {e}")
        return None
    
    except Exception as e:
        print(f"토양 수분 센서 예외 발생: {e}")
        return None

def send_data_periodically():
    """주기마다 센서 데이터 장고서버로 전송 및 자동 제어 실행"""
    tem_humi_data = _read_tem_humi_data()
    soil_moi_data = _read_soil_moisture_data()
    
    if tem_humi_data is None or soil_moi_data is None:
        print("센서 데이터가 None입니다. 전송생략")
        return

    merged_data = {**tem_humi_data, **soil_moi_data}
    
    # ===== 자동 제어 로직 실행 =====
    current_humidity = tem_humi_data.get('humidity')
    current_soil_moisture = soil_moi_data.get('soil_moisture')
    
    if current_humidity is not None:
        auto_humidifier_control(current_humidity)
    
    if current_soil_moisture is not None:
        auto_pump_control(current_soil_moisture)
    
    # 장고 서버로 데이터 전송
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(POST_SENSOR_DATAS_URL, json=merged_data, headers=headers)
        if response.status_code == 200:
            print("서버에 데이터 전송 성공:", response.json())
        else:
            print("서버 응답 에러:", response.status_code, response.text)
    except Exception as e:
        print("서버 전송 실패:", e)
        
def get_setting_soil_moisture_threshold():
    """장고서버에 저장돼있는 토양수분 기준값 get요청"""
    global current_soil_moisture_threshold
    
    try:
        response = requests.get(GET_SOIL_MOISTURE_THRESHOLD_URL)
        if response.status_code == 200:
            data = response.json()
            value = data.get('value', {}).get('soil_moisture_threshold')
            
            if value is not None:
                current_soil_moisture_threshold = float(value)
                print(f"✅ 토양수분 임계값 업데이트: {current_soil_moisture_threshold}%")
                save_setting(value)
            else:
                print("토양수분 임계값 없음:", data)
        else:
            print("토양수분 임계값 가져오기 에러:", response.status_code, response.text)
    except Exception as e:
        print("토양수분 임계값 가져오기 예외:", e)

def get_setting_humidity_threshold():
    """장고서버에 저장돼있는 습도 기준값 get요청"""
    global current_humidity_threshold
    
    try:
        response = requests.get(GET_HUMIDITY_THRESHOLD_URL)
        if response.status_code == 200:
            data = response.json()
            value = data.get('value', {}).get('humidity_threshold')  # Django 뷰 수정 필요
            
            if value is not None:
                current_humidity_threshold = float(value)
                print(f"✅ 습도 임계값 업데이트: {current_humidity_threshold}%")
                save_setting(value)
            else:
                print("습도 임계값 없음:", data)
        else:
            print("습도 임계값 가져오기 에러:", response.status_code, response.text)
    except Exception as e:
        print("습도 임계값 가져오기 예외:", e)
        
def background_loop_1():
    """설정값들을 주기적으로 가져오는 루프"""
    while True:
        time.sleep(60)  # 1분마다
        get_setting_soil_moisture_threshold()
        get_setting_humidity_threshold()

def background_loop_2():
    """센서 데이터 전송 및 자동 제어를 주기적으로 실행하는 루프"""
    while True:
        time.sleep(60)  # 1분마다 
        send_data_periodically()

@app.route('/')
def index():
    return jsonify({
        "message": "라즈베리파이 Flask 서버가 작동 중입니다.",
        "auto_control_status": {
            "soil_moisture_threshold": current_soil_moisture_threshold,
            "humidity_threshold": current_humidity_threshold,
            "pump_busy": pump_is_busy,
            "humidifier_busy": humidifier_is_busy
        }
    })

if __name__ == '__main__':
    init_db()
    
    # 시작 시 임계값들을 한 번 가져오기
    print("🚀 서버 시작 - 초기 임계값 설정 중...")
    get_setting_soil_moisture_threshold()
    get_setting_humidity_threshold()
    
    # 백그라운드 스레드 시작
    threading.Thread(target=background_loop_1, daemon=True).start()
    threading.Thread(target=background_loop_2, daemon=True).start()
    
    print("✅ 자동 제어 시스템이 활성화되었습니다!")
    app.run(host='0.0.0.0', port=5000)