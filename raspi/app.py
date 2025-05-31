from flask import Flask, jsonify
import board         
import adafruit_dht   
import time
import smbus
import digitalio
import threading

# 온습도 센서 설정
SENSOR_PIN = board.D23

try:
    dhtDevice = adafruit_dht.DHT11(SENSOR_PIN)
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
duration_seconds = 5

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

app = Flask(__name__)

# 온습도 센서값 전달 함수
@app.route('/sensor/temp', methods=['GET'])
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

# 토양 수분 센서값 전달 함수
@app.route('/sensor/soil', methods=['GET'])
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

    # 스레드를 생성하여 펌프 작동 함수 실행
    pump_thread = threading.Thread(target=_operate_pump_for_duration)

    message = f"워터 펌프 작동을 시작합니다."
    print(message)
    return jsonify({"status": "success", "message": message, "pump_state": "on", "duration": duration_seconds})


if __name__ == '__main__':
    print("스마트화분 API 서버를 시작합니다...")
    # 외부 네트워크(예: Django 서버)에서 접속 가능하도록 host='0.0.0.0' 으로 설정
    app.run(host='0.0.0.0', port=5000)

# 프로그램 종료 시 센서 리소스 정리
# @app.teardown_appcontext
# def teardown_sensor(exception):
#     if dhtDevice is not None:
#         dhtDevice.exit()
