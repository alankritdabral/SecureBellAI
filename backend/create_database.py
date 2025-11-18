import mysql.connector
from mysql.connector import Error
from datetime import datetime

# --- Database Connection ---
try:
    cnx = mysql.connector.connect(
        host="caboose.proxy.rlwy.net",
        port=47531,
        user="root",
        password="UaUKSJDpFWOmEtMbgKzwaqRSjvWiiIee",
        database="railway"  # Railway DB name (you can create quizo inside it)
    )
    if cnx.is_connected():
        print("✅ Connected to Railway MySQL database successfully!")

except Error as e:
    print("railway busy")
    cnx = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Shashidabral410@",
        database="quizo"  
    )

# --- Logger Function ---
def log_with_timestamp(message):
    """Log messages with a timestamp into report.txt"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("report.txt", "a") as file:
        file.write(f"[{timestamp}] {message}\n")


# --- Table Creation ---
def create_tables():
    """Create all necessary tables if they don't already exist"""
    try:
        cursor = cnx.cursor()

        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create password_reset_temp table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_temp (
            email VARCHAR(250) NOT NULL,
            `key` VARCHAR(250) NOT NULL,
            expDate DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create visitors table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            visitor_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            verified BOOLEAN NOT NULL,
            image TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create recent_visitors table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_visitors (
            visit_id INT AUTO_INCREMENT PRIMARY KEY,
            visitor_id INT,
            image TEXT,
            date DATE,
            time TIME,
            FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cnx.commit()
        log_with_timestamp("✅ All tables created successfully (if not exist).")
        print("✅ Tables created successfully!")

    except Error as err:
        log_with_timestamp(f"❌ Error creating tables: {err}")
        print(f"❌ Error creating tables: {err}")
    finally:
        cursor.close()


# --- Example Operations ---
def get_all_users():
    """Fetch all records from users table"""
    try:
        cursor = cnx.cursor()
        cursor.execute("SELECT * FROM users;")
        rows = cursor.fetchall()

        log_with_timestamp("Fetched all user details:")
        for row in rows:
            log_with_timestamp(f"{row}")

        cursor.close()
        return rows

    except Error as e:
        log_with_timestamp(f"Error fetching users: {e}")
        return []


# --- Main Execution ---
if __name__ == "__main__":
    create_tables()   # ✅ Create tables if not exist
    print("\nAll Users:")
    users = get_all_users()
    for u in users:
        print(u)
