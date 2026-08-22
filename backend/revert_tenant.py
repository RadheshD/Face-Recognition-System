import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def revert_database():
    db_path = os.path.join(os.path.dirname(__file__), "attendance.db")
    if not os.path.exists(db_path):
        logger.info("No attendance.db found, skipping drop.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = ["admins", "employees", "cameras", "attendance"]
    
    for table in tables:
        try:
            # Check if column exists
            cur.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cur.fetchall()]
            
            if "tenant_id" in columns:
                cur.execute(f"ALTER TABLE {table} DROP COLUMN tenant_id")
                logger.info(f"Dropped tenant_id column from '{table}'")
            else:
                logger.info(f"tenant_id not found in '{table}', skipping.")
        except Exception as e:
            logger.error(f"Error dropping tenant_id from {table}: {e}")

    try:
        cur.execute("DROP TABLE IF EXISTS tenants")
        logger.info("Dropped 'tenants' table completely.")
    except Exception as e:
        logger.error(f"Error dropping 'tenants' table: {e}")

    conn.commit()
    conn.close()
    logger.info("Reversion complete.")

if __name__ == "__main__":
    revert_database()
