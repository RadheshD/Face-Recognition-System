import sqlite3

def fix_all_tables():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    tables = cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
    for name, sql in tables:
        if sql and 'BIGINT' in sql.upper():
            print(f"Table {name} has BIGINT:")
            print(sql)

if __name__ == "__main__":
    fix_all_tables()
