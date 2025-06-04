from flask import Flask, jsonify
import threading
import time
import requests
import json
from db import init_db, save_setting

app = Flask(__name__)

POST_SENSOR_DATAS_URL = "http://127.0.0.1:8000/sensor/receive/" 

GET_SOIL_MOISTURE_THRESHOLD_URL = "http://127.0.0.1:8000/soil_moisture_threshold/"

def get_setting_soil_moisture_threshold():
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
        
def background_loop_1(): # 기준 토양수분 받는 스레드함수
    while True:
        get_setting_soil_moisture_threshold()
        time.sleep(60)  # 테스트로 1분 마다 

def background_loop_2(): 
    while True:
        send_data_periodically()
        time.sleep(60)  # 테스트로 1분 마다 
           
def get_sensor_data(): # 실제 센서에서 읽는 값으로 대치
    soil_moisture = 45.3
    temperature = 23.7
    humidity = 55.1
    return {
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity
    }

def send_data_periodically(): # 주기마다 센서 데이터 장고서버로 전송 
    data = get_sensor_data()
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(POST_SENSOR_DATAS_URL, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            print("서버에 데이터 전송 성공:", response.json())
        else:
            print("서버 응답 에러:", response.status_code, response.text)
    except Exception as e:
        print("서버 전송 실패:", e)
        
        
@app.route('/sensor/temp', methods=['GET'])
@app.route('/sensor/humi', methods=['GET'])
def get_tem_humi_data(): # 실제 센서에서 읽는 값으로 바꾸세요

    temperature = 23.7
    humidity = 55.1
    return jsonify({
        "temperature": temperature,
        "humidity": humidity
    })
    
@app.route('/sensor/soil', methods=['GET']) 
def get_soil_moisture_data():
    # 실제 센서에서 읽는 값으로 바꾸세요
    
    soil_moisture = 41.1
    return jsonify({
        "soil_moisture": soil_moisture,
    })
    

@app.route('/')
def index():
    return jsonify({"message": "라즈베리파이 Flask 서버가 작동 중입니다."})

if __name__ == '__main__':
    init_db() #db 초기화
    threading.Thread(target=background_loop_1, daemon=True).start()  # 백그라운드로 실행
    #별도 스레드에서 5분마다 데이터 전송 실행
    threading.Thread(target=background_loop_2, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
