import sqlite3
from datetime import datetime

DB_PATH = "local_data.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS soil_moisture_threshold (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                threshold_value REAL,
                received_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humidity_threshold (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                threshold_value REAL,
                received_at TEXT
            )
        ''')
        
        conn.commit()
        print("DB 초기화 완료")
    except Exception as e:
        print("DB 초기화 실패:", e)
    finally:
        conn.close()

# def save_setting(value):
#     try:
        
#         value = value['soil_moisture_threshold']  # 안전하게 float으로 변환
#         now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#         cursor.execute('''
#             INSERT INTO settings (value, received_at)
#             VALUES (?, ?)
#         ''', (value, now))
#         conn.commit()
#         print(f"값 저장됨: value={value}, time={now}")
#     except Exception as e:
#         print("저장 실패:", e)
#     finally:
#         conn.close()
        
def save_soil_moisture_threshold(threshold_value):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO soil_moisture_threshold (threshold_value, received_at)
            VALUES (?, ?)
        ''', (threshold_value, now))
        conn.commit()
        print(f"토양 수분 임계값 저장됨: {threshold_value}, 시간: {now}")
    except Exception as e:
        print(f"토양 수분 임계값 저장 실패: {e}")
    finally:
        conn.close()
        
def save_humidity_threshold(threshold_value):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO humidity_threshold (threshold_value, received_at)
            VALUES (?, ?)
        ''', (threshold_value, now))
        conn.commit()
        print(f"습도 임계값 저장됨: {threshold_value}, 시간: {now}")
    except Exception as e:
        print(f"습도 임계값 저장 실패: {e}")
    finally:
        conn.close()

