import mysql.connector
from datetime import datetime
import os
import uuid

# Environment-based MySQL config (for Railway or local)
mysql_user = os.getenv("MYSQLUSER", "root")
mysql_password = os.getenv("MYSQLPASSWORD", "Shashidabral410@")
mysql_host = os.getenv("MYSQLHOST", "localhost")
mysql_database = os.getenv("MYSQLDATABASE", "quizo")

# Database configuration
DB_CONFIG = {
    "host": mysql_host,
    "user": mysql_user,
    "password": mysql_password,
    "database": mysql_database
}

def get_connection():
    """Create and return a new MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"[ERROR] MySQL connection failed: {err}")
        return None

def getdetails(visitor_id):
    """Retrieve details of a visitor from the visitors table."""
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM visitors WHERE visitor_id = %s", (visitor_id,))
    visitor = cursor.fetchone()
    cursor.close()
    conn.close()
    return visitor

def detected_unknown(image_path):
    """
    Log an unknown visitor:
    1. Insert placeholder into visitors table
    2. Rename the image to match visitor_id
    3. Update visitors table with new image path
    4. Insert into recent_visitors
    Returns final image path.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    unique_name = f"U_{uuid.uuid4().hex[:8]}"

    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor()

    # Step 1: Insert placeholder visitor
    cursor.execute("""
        INSERT INTO visitors (name, verified, image)
        VALUES (%s, %s, %s)
    """, (unique_name, 0, None))
    visitor_id = cursor.lastrowid

    # Step 2: Rename image file
    new_image_name = f"{visitor_id}.jpg"
    new_image_path = os.path.join(os.path.dirname(image_path), new_image_name)

    try:
        os.rename(image_path, new_image_path)
    except FileNotFoundError:
        print(f"[WARNING] Image not found: {image_path}")

    # Step 3: Update visitors table with image path
    cursor.execute("""
        UPDATE visitors SET image = %s WHERE visitor_id = %s
    """, (new_image_path, visitor_id))

    # Step 4: Insert into recent_visitors
    cursor.execute("""
        INSERT INTO recent_visitors (visitor_id, image, date, time)
        VALUES (%s, %s, %s, %s)
    """, (visitor_id, new_image_path, date_str, time_str))

    conn.commit()
    cursor.close()
    conn.close()

    return new_image_path

def detected_known(visitor_id, image_path):
    """
    Log a known visitor into recent_visitors.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO recent_visitors (visitor_id, image, date, time)
        VALUES (%s, %s, %s, %s)
    """, (visitor_id, image_path, date_str, time_str))

    conn.commit()
    cursor.close()
    conn.close()

    return True
