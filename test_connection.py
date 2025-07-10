# test_connection.py
# A simple script to isolate and test the database connection.

from config_manager import get_config
import pyodbc

def test_cw_connection():
    """
    Attempts a single, isolated connection to the ConnectWise database
    and prints the result.
    """
    print("--- RUNNING ISOLATED CONNECTION TEST ---")
    
    try:
        # Read credentials directly from the config file
        server = get_config('ConnectWiseDB', 'Server')
        database = get_config('ConnectWiseDB', 'DatabaseName')
        username = get_config('ConnectWiseDB', 'User')
        password = get_config('ConnectWiseDB', 'Password')

        print(f"Attempting to connect with the following parameters:")
        print(f"  - Server: {server}")
        print(f"  - Database: {database}")
        print(f"  - User: {username}")
        
        # Build the connection string
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
        )

        # Attempt to connect
        conn = pyodbc.connect(conn_str, timeout=5)
        
        print("\n******************************************")
        print(">>> SUCCESS: Connection to ConnectWise DB was successful!")
        print("******************************************")

        # Optional: Try to run a simple query
        print("\nAttempting to run a simple query...")
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 Member_Full_Name FROM dbo.v_rpt_Member;")
        row = cursor.fetchone()
        if row:
            print(f">>> QUERY SUCCESS: Fetched data for: {row.Member_Full_Name}")
        else:
            print(">>> QUERY WARNING: Connected, but could not fetch data from v_rpt_Member.")

        conn.close()

    except pyodbc.Error as ex:
        print("\n******************************************")
        print(">>> FAILURE: The isolated connection test FAILED.")
        print(">>> This confirms the issue is with the database connection itself,")
        print(">>> not the Flask application logic.")
        print("******************************************")
        # Print the full error from the database driver
        sqlstate = ex.args[0]
        print(f"\nSQLSTATE: {sqlstate}")
        print(f"Error Details: {ex}")
    
    except Exception as e:
        print(f"\nAn unexpected Python error occurred: {e}")

if __name__ == '__main__':
    test_cw_connection()
