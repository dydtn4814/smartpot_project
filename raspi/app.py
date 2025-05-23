from flask import Flask, jsonify
import board          # CircuitPython-Blinka 라이브러리
import adafruit_dht   # DHT 센서 라이브러리
import time

# --- 1. 센서 및 GPIO 핀 설정 ---
# DHT11 센서의 DATA 핀이 연결된 GPIO 핀 번호를 입력합니다.
# 예: GPIO 4번 핀에 연결했다면 board.D4 로 설정합니다.
# 사용하는 핀 번호에 맞게 반드시 수정해주세요!
SENSOR_PIN = board.D4

# DHT11 센서 객체 초기화
# 만약 DHT22 센서를 사용한다면 adafruit_dht.DHT22(SENSOR_PIN) 으로 변경
try:
    dhtDevice = adafruit_dht.DHT11(SENSOR_PIN)
except Exception as e:
    # 라이브러리 초기화 실패 시 (예: libgpiod 관련 문제)
    print(f"센서 초기화 실패: {e}")
    # 프로그램 종료 또는 대체 로직 수행
    dhtDevice = None

# --- 2. Flask 앱 초기화 ---
app = Flask(__name__)

# --- 3. API 엔드포인트 정의 ---
@app.route('/sensor', methods=['GET'])
def get_sensor_data():
    if dhtDevice is None:
        return jsonify({"error": "Sensor not initialized"}), 500
        
    try:
        # 센서로부터 온도와 습도를 읽어옵니다.
        # 센서가 불안정할 수 있어, 읽기에 실패하면 RuntimeError가 발생할 수 있습니다.
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        # 센서 읽기에 성공했는지 확인
        if temperature_c is not None and humidity is not None:
            print(f"측정 성공: Temp={temperature_c:.1f}C, Humidity={humidity}%")
            # JSON 형식으로 성공 응답 반환
            return jsonify({
                "temperature": temperature_c,
                "humidity": humidity
            })
        else:
            # 값 읽기 실패 (None 반환)
            return jsonify({"error": "Failed to retrieve data from sensor. Please try again."}), 500

    except RuntimeError as error:
        # 센서 데이터 읽기 실패 시 발생하는 일반적인 오류
        print(f"센서 읽기 오류: {error.args[0]}")
        return jsonify({"error": str(error)}), 500
    
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"예외 발생: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

# --- 4. Flask 서버 실행 ---
if __name__ == '__main__':
    print("스마트화분 API 서버를 시작합니다...")
    # 외부 네트워크(예: Django 서버)에서 접속 가능하도록 host='0.0.0.0' 으로 설정
    app.run(host='0.0.0.0', port=5000)

# 프로그램 종료 시 센서 리소스 정리
# 이 부분은 서버를 정상적으로 종료할 때 호출되도록 별도 처리가 필요할 수 있습니다.
# @app.teardown_appcontext
# def teardown_sensor(exception):
#     if dhtDevice is not None:
#         dhtDevice.exit()