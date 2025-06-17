# app.py 자동화 시스템 상세 설명

## 🎯 자동화 시스템 개요

라즈베리파이가 **센서 데이터를 읽어서** → **임계값과 비교** → **조건에 맞으면 자동으로 펌프/가습기 작동**하는 시스템입니다.

---

## 🔧 핵심 구성 요소

### 1. **전역 변수들**
```python
# 자동 제어를 위한 전역 변수
current_soil_moisture_threshold = None    # 토양수분 기준값
current_humidity_threshold = None         # 습도 기준값
last_auto_pump_time = 0                  # 마지막 펌프 작동 시간
last_auto_humidifier_time = 0            # 마지막 가습기 작동 시간
AUTO_CONTROL_COOLDOWN = 300              # 5분 쿨다운 (재작동 방지)
```

### 2. **자동 제어 함수들**

#### **🚰 자동 급수 제어 (`auto_pump_control`)**
```python
def auto_pump_control(current_soil_moisture):
    # 조건 체크:
    # 1. 토양수분 < 임계값
    # 2. 쿨다운 시간 경과 (5분)
    # 3. 펌프가 작동중이지 않음
    
    if (current_soil_moisture < current_soil_moisture_threshold and 
        current_time - last_auto_pump_time > AUTO_CONTROL_COOLDOWN and 
        not pump_is_busy):
        
        # 🚨 자동 급수 실행!
        pump_is_busy = True
        last_auto_pump_time = current_time
        # 백그라운드 스레드로 펌프 3초 작동
```

#### **💧 자동 가습기 제어 (`auto_humidifier_control`)**
```python
def auto_humidifier_control(current_humidity):
    # 조건 체크:
    # 1. 습도 < 임계값
    # 2. 쿨다운 시간 경과 (5분)
    # 3. 가습기가 작동중이지 않음
    
    if (current_humidity < current_humidity_threshold and 
        current_time - last_auto_humidifier_time > AUTO_CONTROL_COOLDOWN and 
        not humidifier_is_busy):
        
        # 🚨 자동 가습기 실행!
        humidifier_is_busy = True
        last_auto_humidifier_time = current_time
        # 백그라운드 스레드로 가습기 3초 작동
```

---

## 🔄 백그라운드 동작 시스템

### **스레드 1: 설정값 동기화 (`background_loop_1`)**
```python
def background_loop_1():
    while True:
        time.sleep(60)  # 1분마다 실행
        get_setting_soil_moisture_threshold()  # Django에서 토양수분 기준값 가져오기
        get_setting_humidity_threshold()       # Django에서 습도 기준값 가져오기
```

**역할**: Django 서버에 저장된 사용자 설정값을 주기적으로 가져와서 자동제어 기준을 업데이트

### **스레드 2: 센서 모니터링 & 자동제어 (`background_loop_2`)**
```python
def background_loop_2():
    while True:
        time.sleep(60)  # 1분마다 실행
        send_data_periodically()  # 센서 읽기 + 자동제어 + 데이터 전송
```

**핵심 함수 `send_data_periodically()`의 동작:**
```python
def send_data_periodically():
    # 1. 센서 데이터 읽기
    tem_humi_data = _read_tem_humi_data()      # 온습도 센서
    soil_moi_data = _read_soil_moisture_data() # 토양수분 센서
    
    # 2. 자동 제어 로직 실행 ⭐
    current_humidity = tem_humi_data.get('humidity')
    current_soil_moisture = soil_moi_data.get('soil_moisture')
    
    if current_humidity is not None:
        auto_humidifier_control(current_humidity)    # 습도 체크 & 자동 가습기
    
    if current_soil_moisture is not None:
        auto_pump_control(current_soil_moisture)     # 토양수분 체크 & 자동 급수
    
    # 3. Django 서버로 데이터 전송
    requests.post(POST_SENSOR_DATAS_URL, json=merged_data)
```

---

## ⚡ 동작 흐름도

```
🔄 1분마다 반복:

📡 센서 데이터 읽기
    ↓
🧮 현재값 vs 임계값 비교
    ↓
❓ 조건 만족?
    ├─ YES → 🚨 자동 장치 작동 (펌프/가습기)
    └─ NO  → ⏭️ 다음 사이클 대기
    ↓
📤 Django 서버로 데이터 전송
    ↓
⏰ 1분 대기 후 반복
```

---

## 🛡️ 안전장치들

### **1. 쿨다운 시스템 (5분)**
```python
AUTO_CONTROL_COOLDOWN = 300  # 5분
```
- 같은 장치가 너무 자주 작동하는 것을 방지
- 펌프: 5분에 한 번만 자동 작동 가능
- 가습기: 5분에 한 번만 자동 작동 가능

### **2. 중복 작동 방지**
```python
pump_is_busy = False      # 펌프 작동 상태 플래그
humidifier_is_busy = False # 가습기 작동 상태 플래그
```
- 장치가 이미 작동 중이면 새로운 명령 무시

### **3. 스레드 안전성**
```python
pump_lock = threading.Lock()
humidifier_lock = threading.Lock()
```
- 여러 스레드에서 동시 접근 시 충돌 방지

---

## 🎮 사용자 제어 vs 자동 제어

### **사용자 수동 제어**
- 카카오톡 챗봇: "물 주기", "가습기 작동"
- 즉시 실행 (busy 상태가 아니면)

### **자동 제어**
- 백그라운드에서 1분마다 체크
- 임계값 기반 자동 실행
- 쿨다운 및 안전장치 적용

---

## 📊 실제 동작 예시

**시나리오**: 토양수분 임계값이 30%로 설정된 상황

```
12:00 - 센서 읽기: 토양수분 35% → 임계값보다 높음 → 아무것도 안함
12:01 - 센서 읽기: 토양수분 25% → 임계값보다 낮음 → 🚨 자동 급수 작동!
12:02 - 센서 읽기: 토양수분 20% → 임계값보다 낮지만 쿨다운 중 → 대기
...
12:06 - 센서 읽기: 토양수분 22% → 쿨다운 끝, 여전히 낮음 → 🚨 다시 급수!
```

이렇게 **완전 자동화된 스마트 식물 관리 시스템**이 구현되어 있습니다! 🌱✨
