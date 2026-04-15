# test_db_connection.py
import os
import sys
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')  # Change to your project name

# Test MySQL connection without Django ORM
import pymysql
import socket

def test_mysql_connection():
    print("=== MySQL Connection Debug ===")
    
    # Get connection parameters
    db_config = {
        'host': os.getenv('DB_HOST', 'db'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', ''),
    }
    
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"User: {db_config['user']}")
    print(f"Database: {db_config['database']}")
    
    # Test host resolution
    print(f"\n1. Testing hostname resolution...")
    try:
        ip = socket.gethostbyname(db_config['host'])
        print(f"✓ Host resolved to: {ip}")
    except socket.gaierror as e:
        print(f"✗ Host resolution failed: {e}")
        return False
    
    # Test connection
    print(f"\n2. Testing MySQL connection...")
    try:
        conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            connect_timeout=5
        )
        print("✓ Successfully connected to MySQL!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✓ MySQL Version: {version[0]}")
        
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()
        print(f"✓ Current Database: {db_name[0]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_mysql_connection()
    sys.exit(0 if success else 1)