import mysql.connector
from datetime import datetime

# Create a connection to the database
cnx = mysql.connector.connect(
    host="localhost", 
    user="root", 
    password="Shashidabral410@", 
    database="quizo"
)

def log_with_timestamp(message):
    """Helper function to log messages with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('report.txt', 'a') as file:
        file.write(f"[{timestamp}] {message}\n")

def get_all_details():
    cursor = cnx.cursor()

    query = "SELECT * FROM sign_up"
    cursor.execute(query)

    rows = cursor.fetchall()

    log_with_timestamp("Fetched all sign-up details:")
    for row in rows:
        log_with_timestamp(f"{row}")
    
    cursor.close()

def insert_signup(name, gender, dob, mobile, email, password):
    try:
        # Ensure the database connection is active
        if not cnx.is_connected():
            cnx.reconnect()

        cursor = cnx.cursor()

        query = """
        INSERT INTO sign_up (name, gender, dob, mobile, email, password)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (name, gender, dob, mobile, email, password))
        cnx.commit()
        cursor.close()
        log_with_timestamp(f"Sign-Up data inserted successfully for {email}.")
        print("Sign-Up data credentials inserted successfully!")    
        return 1

    except mysql.connector.Error as err:
        log_with_timestamp(f"Error inserting sign-up credentials for {email}: {err}")
        cnx.rollback()
        return -1
    
    except Exception as e:
        log_with_timestamp(f"An unexpected error occurred during sign-up for {email}: {e}")
        cnx.rollback()
        return -1

def search_login_credentials(email, password):
    try:
        cursor = cnx.cursor()

        # Modify the query to select the name and password
        query = "SELECT name, email, password FROM sign_up WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            name, email, _ = row
            
            # Get the current date and time
            start_time = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")

            # Store the start time in the database
            cursor = cnx.cursor()
            update_query = "UPDATE sign_up SET start_time = NOW() WHERE email = %s"
            cursor.execute(update_query, (email,))
            cnx.commit()
            cursor.close()
            
            log_with_timestamp(f"Login successful for {email}. Start time recorded: {start_time}")
            
            text_to_write = f"Data found for {name}:\nEmail: {email}"
            with open('report.txt', 'w') as file:
                file.write(text_to_write)
            
            print("Login successful. Start time recorded:", start_time)
            return {'username': name, 'message': 'Login successful'}
        else:
            log_with_timestamp(f"Login failed for {email}. No data found.")
            print("No data found.")
            return None

    except mysql.connector.Error as err:
        log_with_timestamp(f"Error during login process for {email}: {err}")
        return None

    except Exception as e:
        log_with_timestamp(f"An unexpected error occurred during login for {email}: {e}")
        return None

def save_score(email, score, total_questions, violations):
    try:
        cursor = cnx.cursor()

        # Calculate percentage score
        percentage = (score / total_questions) * 100

        # Fetch the current time as the time_taken value
        time_taken = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")

        # Update the database with the final score, time taken, and violation scale
        query = """
        UPDATE sign_up 
        SET total_score = %s, 
            percentage = %s, 
            time_taken = %s, 
            violation_scale = %s, 
            attempted = %s
        WHERE email = %s
        """
        cursor.execute(query, (score, percentage, time_taken, violations, total_questions, email))
        cnx.commit()
        cursor.close()
        log_with_timestamp(f"Score saved for {email}: {score}/{total_questions} ({percentage:.2f}%), Violations: {violations}")
        print(f"Score for {email} saved successfully with a percentage of {percentage:.2f}%.")
        return 1

    except mysql.connector.Error as err:
        log_with_timestamp(f"Error saving score for {email}: {err}")
        cnx.rollback()
        return -1
    
    except Exception as e:
        log_with_timestamp(f"An unexpected error occurred while saving score for {email}: {e}")
        cnx.rollback()
        return -1

# Example usage:
# save_score('newuser@gmail.com', 5, 6, 2)


if __name__ == "__main__":
    print("All Sign-Up Details:")
    get_all_details()
    # Example usage:
    # print(search_login_credentials('kumar1166@gmail.com', 'Krishna1'))
    # insert_signup('New User', 'Male', '2000-01-01', '1234567890', 'newuser@gmail.com', 'newpassword')
    # print("Updated Sign-Up Details:")
    # get_all_details()
