import pyodbc
import configparser
from datetime import datetime, timedelta
from config_manager import get_config

def get_db_connection():
    """Establishes a connection to the primary GTS-QADB SQL Server database."""
    server = get_config('Database', 'Server')
    database = get_config('Database', 'DatabaseName')
    username = get_config('Database', 'User')
    password = get_config('Database', 'Password')

    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
    )

    try:
        conn = pyodbc.connect(conn_str, autocommit=False)
        return conn
    except pyodbc.Error as ex:
        raise

def get_cw_db_connection():
    """Establishes a read-only connection to the ConnectWise SQL Server database."""
    server = get_config('ConnectWiseDB', 'Server')
    database = get_config('ConnectWiseDB', 'DatabaseName')
    username = get_config('ConnectWiseDB', 'User')
    password = get_config('ConnectWiseDB', 'Password')

    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
    )

    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        return conn
    except pyodbc.Error as ex:
        raise
        
def get_active_profiles():
    """Fetches all active QA profiles from the local QA database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT RecID, Name FROM dbo.ProfileHeader WHERE ActiveFlag = 1 ORDER BY Name")
    
    columns = [column[0] for column in cursor.description]
    profiles = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return profiles

def get_all_members():
    """
    Fetches all active, non-managerial technicians directly from the
    ConnectWise database (v_rpt_Member), which serves as the single source of truth.
    """
    conn = get_cw_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT [Member_RecID], [Member_Full_Name], [Email_Address]
        FROM [cwwebapp_globaltsllc].[dbo].[v_rpt_Member]
        WHERE [Member_Type_Desc] NOT IN ('C-Suite','IT Director','SubContractor')
        AND [Member_Type_Desc] NOT LIKE '%manager%'
        AND Inactive_Flag = '0'
        AND [Member_Type_Desc] IN ('First Call Tech', 'Jr. Sys Admin', 'Sys Admin', 'Dispatcher')
        ORDER BY [Member_Full_Name];
    """
    cursor.execute(query)

    columns = [column[0] for column in cursor.description]
    members = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return members

def get_profile_questions(profile_id):
    """Fetches all questions for a given profile ID from the local QA database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT ProfileRecID, SectionRecID, QualityRecID, ProfileName, SectionName, Question, SectionOrder, QuestionOrder, Points
        FROM dbo.v_ProfileSummary
        WHERE ProfileRecID = ?
        ORDER BY SectionOrder, QuestionOrder;
    """
    cursor.execute(query, profile_id)
    
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return results

def _ensure_member_exists_in_qa_db(member_rec_id, member_full_name):
    """
    Helper function to sync a member from ConnectWise to the local QA database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Member_Full_Name FROM dbo.Members WHERE Member_RecID = ?", member_rec_id)
        result = cursor.fetchone()
        
        if result:
            if result.Member_Full_Name != member_full_name:
                cursor.execute("UPDATE dbo.Members SET Member_Full_Name = ? WHERE Member_RecID = ?", member_full_name, member_rec_id)
        else:
            cursor.execute("INSERT INTO dbo.Members (Member_RecID, Member_Full_Name) VALUES (?, ?)", member_rec_id, member_full_name)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def save_review_to_db(review_id, date_executed, executed_by, member_rec_id, member_full_name, profile_id, score, comment, ticket_nbr, answers):
    """Saves a complete review to the database, ensuring the member exists first."""
    _ensure_member_exists_in_qa_db(member_rec_id, member_full_name)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    answer_tuples = [(float(a['score']), a['profile_id'], a['section_id'], a['question_id'], a['observation']) for a in answers]

    sql = """
        EXEC [dbo].[sp_SaveCompleteReview] @Review_RecID=?, @Date_Executed=?, @Executed_By=?, 
        @Member_RecID=?, @Member_FullName=?, @Profile_ID=?, @Score=?, @Comment=?, 
        @TicketNbr=?, @Answers=?;
    """
    
    try:
        cursor.execute(sql, review_id, date_executed, executed_by, member_rec_id, member_full_name, profile_id, score, comment, ticket_nbr, answer_tuples)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_filtered_reviews(filters):
    """Fetches review data based on a dictionary of filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM dbo.TheReviews WHERE 1=1"
    params = []

    if filters.get('technician_id') and filters['technician_id'] != 'all':
        query += " AND Member_Recid = ?"
        params.append(int(filters['technician_id']))
    
    if filters.get('profile_id') and filters['profile_id'] != 'all':
        query += " AND Profile_ID = ?"
        params.append(int(filters['profile_id']))

    if filters.get('start_date') and filters['start_date'] != '':
        query += " AND Date_Executed >= ?"
        params.append(filters['start_date'])

    if filters.get('end_date') and filters['end_date'] != '':
        end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d').date()
        next_day = end_date + timedelta(days=1)
        query += " AND Date_Executed < ?"
        params.append(str(next_day))

    query += " ORDER BY Date_Executed DESC, Member_FullName, SortOrder"
    
    cursor.execute(query, params)
    
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return results

def get_review_by_id(review_id):
    """Fetches all data for a single review by its GUID from the canonical view."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM dbo.TheReviews WHERE Review_RecID = ? ORDER BY SortOrder"
    cursor.execute(query, review_id)
    
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return results

def get_tech_review_worklist():
    """
    Gets a list of all technicians from ConnectWise and joins it with the date of their last review.
    """
    all_techs = get_all_members()

    conn_qa = get_db_connection()
    cursor_qa = conn_qa.cursor()
    cursor_qa.execute("SELECT Member_RecID, MAX(Date_Executed) AS LastReviewDate FROM dbo.Reviews GROUP BY Member_RecID")
    
    review_dates = {row.Member_RecID: row.LastReviewDate for row in cursor_qa.fetchall()}
    conn_qa.close()

    worklist = []
    for tech in all_techs:
        last_review_date = review_dates.get(tech['Member_RecID'])
        worklist.append({
            'Member_RecID': tech['Member_RecID'],
            'Member_Full_Name': tech['Member_Full_Name'],
            'LastReviewDate': last_review_date
        })
        
    worklist.sort(key=lambda x: (x['LastReviewDate'] is None, x['LastReviewDate'], x['Member_Full_Name']))

    return worklist

def delete_review_by_id(review_id):
    """
    Deletes a review from the database.
    This assumes that ON DELETE CASCADE is enabled on the foreign key
    in the dbo.Answers table, which will automatically delete child records.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM dbo.Reviews WHERE Review_RecID = ?", review_id)
        conn.commit()
        # Check if any rows were affected to confirm deletion
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Could not delete review {review_id}. Reason: {e}")
        raise
    finally:
        conn.close()
