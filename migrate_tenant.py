import sqlite3
import datetime

def migrate_tenant_schema():
    conn = sqlite3.connect('backend/attendance.db')
    cursor = conn.cursor()
    
    try:
        # Create tenants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            organization_type VARCHAR(50) DEFAULT 'school',
            created_at DATETIME
        )
        ''')
        
        # Insert default tenant if not exists
        cursor.execute("SELECT id FROM tenants WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO tenants (id, name, organization_type, created_at)
            VALUES (1, 'Default Organization', 'school', ?)
            ''', (datetime.datetime.utcnow(),))
        
        # Use simple ALTER TABLE where sqlite supports it, or PRAGMA statements
        tables_to_migrate = ['admins', 'employees', 'cameras', 'attendance']
        
        for table in tables_to_migrate:
            # Check if tenant_id column already exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'tenant_id' not in columns:
                print(f"Adding tenant_id to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE")
                
                # Update existing rows to belong to default tenant
                cursor.execute(f"UPDATE {table} SET tenant_id = 1 WHERE tenant_id IS NULL")
                print(f"Updated existing records in {table} to tenant_id = 1")
        
        conn.commit()
        print("MIGRATION_SUCCESS: Tenant isolation schema applied.")
    except Exception as e:
        conn.rollback()
        print("MIGRATION_FAILED:", str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_tenant_schema()
