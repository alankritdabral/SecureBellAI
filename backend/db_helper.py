import mysql.connector
from datetime import datetime
from mysql.connector import Error

def create_connection():
    """Create and return a new MySQL connection."""
    try:
        conn = mysql.connector.connect(
            host="caboose.proxy.rlwy.net",
            port=47531,
            user="root",
            password="UaUKSJDpFWOmEtMbgKzwaqRSjvWiiIee",
            database="railway"
        )
        if conn.is_connected():
            print("[INFO] Connected to Railway MySQL successfully.")
        return conn

    except Error as e:
        print("railway busy, switching to local DB")
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Shashidabral410@",
                database="quizo"
            )
            if conn.is_connected():
                print("[INFO] Connected to Local MySQL successfully.")
            return conn
        except Error as e2:
            print("[ERROR] Both Railway & Local DB failed:", e2)
            return None

# Global connection
cnx = create_connection()

def log_with_timestamp(message):
    """Helper function to log messages with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("report.txt", "a") as file:
        file.write(f"[{timestamp}] {message}\n")

def get_all_details():
    """Fetch and log all users from the database."""
    try:
        if not cnx.is_connected():
            cnx.reconnect()

        cursor = cnx.cursor()
        cursor.execute("SELECT * FROM users")  # ✅ fixed table name
        rows = cursor.fetchall()

        log_with_timestamp("Fetched all sign-up details:")
        for row in rows:
            log_with_timestamp(f"{row}")

        cursor.close()
        print(f"[INFO] Retrieved {len(rows)} users successfully.")

    except Error as e:
        log_with_timestamp(f"[ERROR] Failed to fetch details: {e}")
        print(f"[ERROR] Failed to fetch details: {e}")

def insert_signup(username, email, password):
    """Insert a new signup record."""
    try:
        if not cnx.is_connected():
            cnx.reconnect()

        cursor = cnx.cursor()
        query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, email, password))
        cnx.commit()
        cursor.close()

        log_with_timestamp(f"Inserted sign-up credentials for {email}")
        print("[INFO] Sign-up data inserted successfully.")
        return 1

    except Error as err:
        log_with_timestamp(f"[ERROR] Inserting credentials for {email}: {err}")
        if cnx.is_connected():
            cnx.rollback()
        return -1

def search_login_credentials(email, password):
    """Search user credentials and verify login."""
    try:
        if not cnx.is_connected():
            cnx.reconnect()

        cursor = cnx.cursor()
        query = "SELECT email, password FROM users WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            log_with_timestamp(f"Login failed for {email}: No user found.")
            print("[INFO] No matching user found.")
            return False

        searched_email, searched_password = row
        if searched_email == email and searched_password == password:
            log_with_timestamp(f"Login successful for {email}.")
            print("[SUCCESS] Login successful!")
            return True
        else:
            log_with_timestamp(f"Login failed for {email}: Incorrect password.")
            print("[INFO] Incorrect credentials.")
            return False

    except Error as err:
        log_with_timestamp(f"[ERROR] During login process for {email}: {err}")
        print(f"[ERROR] Database error: {err}")
        return None

if __name__ == "__main__":
    print("All Sign-Up Details:")
    get_all_details()
