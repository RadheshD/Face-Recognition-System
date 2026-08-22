import sqlite3
import os

def fix_schema():
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'attendance.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    table_sql = cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'").fetchone()
    if table_sql:
        print("TABLE SCHEMA:\n", table_sql[0])
        
    try:
        # Check if autoincrement works
        cursor.execute("INSERT INTO attendance (employee_id, event_type, timestamp, created_at) VALUES (1, 'TEST', '2022', '2022')")
        inserted = cursor.lastrowid
        print("Successfully inserted without ID. Row ID:", inserted)
        cursor.execute(f"DELETE FROM attendance WHERE id={inserted}")
        conn.commit()
    except Exception as e:
        print("Insert failed:", e)

    conn.close()

if __name__ == "__main__":
    fix_schema()
