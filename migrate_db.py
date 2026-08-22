import sqlite3

def migrate_attendance_schema():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    try:
        # Create the new table
        cursor.execute("""
        CREATE TABLE attendance_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            employee_id INTEGER NOT NULL, 
            camera_id INTEGER, 
            event_type VARCHAR(20) NOT NULL, 
            timestamp DATETIME NOT NULL, 
            confidence FLOAT, 
            is_live BOOLEAN, 
            liveness_score FLOAT, 
            source VARCHAR(50), 
            note TEXT, 
            created_at DATETIME, 
            FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE, 
            FOREIGN KEY(camera_id) REFERENCES cameras (id) ON DELETE SET NULL
        )
        """)
        
        # Copy data
        cursor.execute("""
        INSERT INTO attendance_new (id, employee_id, camera_id, event_type, timestamp, confidence, is_live, liveness_score, source, note, created_at)
        SELECT id, employee_id, camera_id, event_type, timestamp, confidence, is_live, liveness_score, source, note, created_at FROM attendance
        """)
        
        # Drop old and rename new
        cursor.execute("DROP TABLE attendance")
        cursor.execute("ALTER TABLE attendance_new RENAME TO attendance")
        
        # Re-create indexes if any existed natively
        cursor.execute("CREATE INDEX ix_attendance_camera_id ON attendance (camera_id)")
        cursor.execute("CREATE INDEX ix_attendance_employee_id ON attendance (employee_id)")
        cursor.execute("CREATE INDEX ix_attendance_id ON attendance (id)")
        cursor.execute("CREATE INDEX ix_attendance_timestamp ON attendance (timestamp)")
        
        conn.commit()
        print("MIGRATION_SUCCESS")
    except Exception as e:
        conn.rollback()
        print("MIGRATION_FAILED:", str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_attendance_schema()
