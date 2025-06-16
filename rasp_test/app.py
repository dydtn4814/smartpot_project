from flask import Flask, jsonify
import threading
import time
import requests
import board
import adafruit_dht
import smbus
import digitalio
import json
from db import init_db, save_setting

app = Flask(__name__)

POST_SENSOR_DATAS_URL = "http://192.168.0.34:8000/sensor/receive/"  #네트워크 바꾸고 , 장고서버 열떄 python manage.py runserver 0.0.0.0:8000

GET_SOIL_MOISTURE_THRESHOLD_URL = "http://127.0.0.1:8000/soil_moisture_threshold/"


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

@app.route('/sensor/temp', methods=['GET']) # 장고서버에서 온습도 요청시 실행
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


# 토양 수분 센서값 전달 함수
@app.route('/sensor/soil', methods=['GET']) # 장고서버에서 토양수분 요청시 실행
def get_soil_moisture_data():
    if bus is None: # smbus 초기화 실패 시
        return jsonify({"error": "I2C 버스 초기화 실패"}), 500
        
    try:
        bus.write_byte(address, A0)

        # time.sleep(0.01) 

        bus.read_byte(address)
        soil_moisture_value = bus.read_byte(address) # 실제 값 (0-255 범위, 8비트)

        # 8비트 ADC (0-255)
        min_moisture_raw = 20 
        max_moisture_raw = 220  
        
        moisture_raw_value = max(min_moisture_raw, min(soil_moisture_value, max_moisture_raw))

        if max_moisture_raw == min_moisture_raw:
             soil_moisture_percentage = 0
        else:
             soil_moisture_percentage = 100 * (1 - (moisture_raw_value - min_moisture_raw) / (max_moisture_raw - min_moisture_raw)) # 습할수록 raw 값이 낮아지는 저항성 센서 가정

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


def _read_tem_humi_data(): #send_data_periodically() 을 위한 내부함수
    if dhtDevice is None:
        print("error: Sensor not initialized")
        return                  
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        if temperature_c is not None and humidity is not None:
            print(f"send_data_periodically() 측정 성공: Temp={temperature_c:.1f}C, Humidity={humidity}%")
            
            return {
                "temperature": temperature_c,
                "humidity": humidity
            }
        else:
            print("error: Failed to retrieve data from sensor. Please try again.")
            return

    except RuntimeError as error:
        print(f"센서 읽기 오류: {error.args[0]}")
        return 
    
    except Exception as e:
        print(f"예외 발생: {e}")
        return 
    
def _read_soil_moisture_data(): # send_data_periodically() 을 위한 내부함수
    if bus is None: # smbus 초기화 실패 시
        print("error: I2C 버스 초기화 실패")
        return 
        
    try:
        bus.write_byte(address, A0)

        # time.sleep(0.01) 

        bus.read_byte(address)
        soil_moisture_value = bus.read_byte(address) # 실제 값 (0-255 범위, 8비트)

        # 8비트 ADC (0-255)
        min_moisture_raw = 20 
        max_moisture_raw = 220  
        
        moisture_raw_value = max(min_moisture_raw, min(soil_moisture_value, max_moisture_raw))

        if max_moisture_raw == min_moisture_raw:
             soil_moisture_percentage = 0
        else:
             soil_moisture_percentage = 100 * (1 - (moisture_raw_value - min_moisture_raw) / (max_moisture_raw - min_moisture_raw)) # 습할수록 raw 값이 낮아지는 저항성 센서 가정

        soil_moisture_percentage = round(soil_moisture_percentage, 1)

        print(f"토양 수분 측정 성공: Raw={soil_moisture_value}, Percentage={soil_moisture_percentage}%")
        return ({
            "soil_moisture_percentage": soil_moisture_percentage
        })

    except IOError as e:
        print(f"I/O 오류 발생 (PCF8591): {e}")
        return
    
    except Exception as e:
        print(f"토양 수분 센서 예외 발생: {e}")
        return

def send_data_periodically(): # 주기마다 센서 데이터 장고서버로 전송 
    tem_humi_data = _read_tem_humi_data()       # 센서값 read 하는 내부함수 따로 호출
    soil_moi_data = _read_soil_moisture_data()
    
    merged_data = {**tem_humi_data, **soil_moi_data}
    
    merged_data = json.dumps(merged_data)
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(POST_SENSOR_DATAS_URL, merged_data, headers=headers)
        if response.status_code == 200:
            print("서버에 데이터 전송 성공:", response.json())
        else:
            print("서버 응답 에러:", response.status_code, response.text)
    except Exception as e:
        print("서버 전송 실패:", e)
        
def get_setting_soil_moisture_threshold(): # 장고서버에 저장돼있는 토양수분 기준값 get요청
    try:
        response = requests.get(GET_SOIL_MOISTURE_THRESHOLD_URL)
        if response.status_code == 200:
            data = response.json()
            value = data.get('value')
            
            if value is not None:
                print("받은 토양수분기준 값:", value)
                save_setting(value)
            else:
                print("값 없음:", data)
        else:
            print("에러 응답:", response.status_code, response.text)
    except Exception as e:
        print("예외 발생:", e)
        
def background_loop_1(): # get_setting_soil_moisture_threshold()를 주기적으로 호출
    while True:
        time.sleep(60)  # 테스트로 1분 마다
        get_setting_soil_moisture_threshold()
         

def background_loop_2(): # send_data_periodically()를 주기적으로 호출
    while True:
        time.sleep(60)  # 테스트로 1분 마다 
        send_data_periodically()
        
           


        

# @app.route('/sensor/temp', methods=['GET'])
# @app.route('/sensor/humi', methods=['GET'])
# def get_tem_humi_data(): # 실제 센서에서 읽는 값으로 바꾸세요

#     temperature = 23.7
#     humidity = 55.1
#     return jsonify({
#         "temperature": temperature,
#         "humidity": humidity
#     })
    
# @app.route('/sensor/soil', methods=['GET']) 
# def get_soil_moisture_data():
#     # 실제 센서에서 읽는 값으로 바꾸세요
    
#     soil_moisture = 41.1
#     return jsonify({
#         "soil_moisture": soil_moisture,
#     })
    

@app.route('/')
def index():
    return jsonify({"message": "라즈베리파이 Flask 서버가 작동 중입니다."})

if __name__ == '__main__':
    init_db() #db 초기화
    threading.Thread(target=background_loop_1, daemon=True).start()  # 백그라운드로 실행
    #별도 스레드에서 5분마다 데이터 전송 실행
    threading.Thread(target=background_loop_2, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)