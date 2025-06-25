import sqlite3
from datetime import datetime

DB_PATH = "local_data.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS soil_moisture_threshold (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         threshold_value REAL,
        #         received_at TEXT
        #     )
        # ''')
        
       
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS humidity_threshold (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         threshold_value REAL,
        #         received_at TEXT
        #     )
        # ''')
        
        # 'id INTEGER PRIMARY KEY'로 변경: AUTOINCREMENT는 제거하여 id=1로 명시적 사용에 더 적합하게 합니다.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS soil_moisture_threshold (
                id INTEGER PRIMARY KEY,
                threshold_value REAL,
                received_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humidity_threshold (
                id INTEGER PRIMARY KEY,
                threshold_value REAL,
                received_at TEXT
            )
        ''')
        # 초기 DB 생성 시, ID 1번 레코드가 없으면 기본값을 삽입합니다. 이전에 정한 기준값 없으면 디폴트값  none
        # 이렇게 하면 항상 ID 1번 레코드가 존재하도록 보장됩니다.
        cursor.execute("INSERT OR IGNORE INTO soil_moisture_threshold (id, threshold_value, received_at) VALUES (1, -1, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        cursor.execute("INSERT OR IGNORE INTO humidity_threshold (id, threshold_value, received_at) VALUES (1,-1, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
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
            INSERT OR REPLACE INTO soil_moisture_threshold (id, threshold_value, received_at)
            VALUES (?, ?, ?)
        ''', (1, threshold_value, now)) #id를 항상 1로하여 업데이트
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
            INSERT OR REPLACE INTO humidity_threshold (id, threshold_value, received_at)
            VALUES (?, ?, ?)
        ''', (1, threshold_value, now))
        conn.commit()
        print(f"습도 임계값 저장됨: {threshold_value}, 시간: {now}")
    except Exception as e:
        print(f"습도 임계값 저장 실패: {e}")
    finally:
        conn.close()

