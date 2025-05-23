from flask import Flask, jsonify
import board         
import adafruit_dht   
import time

# --- 1. 센서 및 GPIO 핀 설정 ---
SENSOR_PIN = board.D4

try:
    dhtDevice = adafruit_dht.DHT11(SENSOR_PIN)
except Exception as e:
    print(f"센서 초기화 실패: {e}")
    dhtDevice = None

app = Flask(__name__)

@app.route('/sensor', methods=['GET'])
def get_sensor_data():
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

if __name__ == '__main__':
    print("스마트화분 API 서버를 시작합니다...")
    # 외부 네트워크(예: Django 서버)에서 접속 가능하도록 host='0.0.0.0' 으로 설정
    app.run(host='0.0.0.0', port=5000)

# 프로그램 종료 시 센서 리소스 정리
# @app.teardown_appcontext
# def teardown_sensor(exception):
#     if dhtDevice is not None:
#         dhtDevice.exit()
