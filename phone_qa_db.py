import pyodbc
from config_manager import get_config
from datetime import datetime, timedelta

def get_phone_qa_db_connection():
    """Establishes a connection to the PhoneQA SQL Server database."""
    server = get_config('PhoneQADatabase', 'Server')
    database = get_config('PhoneQADatabase', 'DatabaseName')
    username = get_config('PhoneQADatabase', 'User')
    password = get_config('PhoneQADatabase', 'Password')

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

def get_latest_run_status():
    """
    Fetches status details from the most recent processing run
    of the automated phone QA system.
    """
    conn = get_phone_qa_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT TOP 1
            ProcessingDateTime,
            COUNT(DISTINCT AgentId) AS AgentsProcessed,
            COUNT(*) AS CallsAnalyzed
        FROM 
            dbo.IndividualCallAnalyses
        WHERE 
            ProcessingDateTime IS NOT NULL
        GROUP BY
            ProcessingDateTime
        ORDER BY
            ProcessingDateTime DESC;
    """
    
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        if row:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        else:
            return None 
    finally:
        conn.close()

def get_all_phone_agents():
    """Fetches all agents from the PhoneQA database."""
    conn = get_phone_qa_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT AgentID, AgentName AS FullName FROM dbo.Agents ORDER BY AgentName")
    
    columns = [column[0] for column in cursor.description]
    agents = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return agents

def get_combined_analyses_by_filter(filters):
    """
    Fetches the main combined analysis reports based on filters.
    Includes diagnostic printing to debug any type of error.
    """
    try:
        conn = get_phone_qa_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                ca.CombinedAnalysisID,
                ca.AgentID,
                ag.AgentName,
                ca.AnalysisDateTime,
                ca.AnalysisPeriodNote
            FROM 
                dbo.CombinedAnalyses ca
            JOIN 
                dbo.Agents ag ON ca.AgentID = ag.AgentID
            WHERE 1=1
        """
        params = []

        if filters.get('agent_id') and filters['agent_id'] != 'all':
            query += " AND ca.AgentID = ?"
            params.append(int(filters['agent_id']))

        if filters.get('start_date') and filters['start_date'] != '':
            query += " AND ca.AnalysisDateTime >= ?"
            params.append(filters['start_date'])

        if filters.get('end_date') and filters['end_date'] != '':
            end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d').date()
            next_day = end_date + timedelta(days=1)
            query += " AND ca.AnalysisDateTime < ?"
            params.append(str(next_day))

        query += " ORDER BY ag.AgentName, ca.AnalysisDateTime DESC"
        
        print("\n--- DEBUG: EXECUTING PHONE REPORT LIST QUERY ---")
        print(f"Generated SQL: {query}")
        print(f"Parameters: {params}")
        
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        print("--- DEBUG: Phone report list query executed successfully. ---")
        return results
    except Exception as ex:
        print(f"--- !!! DATABASE ERROR IN phone_qa_db.py (get_combined_analyses_by_filter) !!! ---")
        print(f"Error Type: {type(ex).__name__}")
        print(f"Error Details: {ex}")
        print("--- END DATABASE ERROR ---")
        raise

def get_details_for_combined_analysis(analysis_id):
    """
    Fetches all details for a combined analysis.
    Includes robust diagnostic printing.
    """
    try:
        conn = get_phone_qa_db_connection()
        cursor = conn.cursor()
        details = {}
        
        print(f"\n--- DEBUG: Fetching details for combined analysis ID: {analysis_id} ---")

        header_query = "SELECT ca.AgentID, ag.AgentName, ca.ProcessingDateTime, ca.AnalysisDateTime FROM dbo.CombinedAnalyses ca JOIN dbo.Agents ag ON ca.AgentID = ag.AgentID WHERE ca.CombinedAnalysisID = ?"
        cursor.execute(header_query, analysis_id)
        header_row = cursor.fetchone()
        if not header_row:
            conn.close()
            return {"error": "Header row not found for this Analysis ID."}

        details['header'] = dict(zip([column[0] for column in cursor.description], header_row))
        agent_id = header_row.AgentID
        processing_date_time = header_row.ProcessingDateTime

        cursor.execute("SELECT StrengthText FROM dbo.CombinedAnalysisStrengths WHERE CombinedAnalysisID = ?", analysis_id)
        details['strengths'] = [row.StrengthText for row in cursor.fetchall()]
        
        cursor.execute("SELECT DevelopmentAreaText FROM dbo.CombinedAnalysisDevelopmentAreas WHERE CombinedAnalysisID = ?", analysis_id)
        details['development_areas'] = [row.DevelopmentAreaText for row in cursor.fetchall()]

        calls_query = "SELECT AnalysisID, OriginalAudioFileName, CallDateTime, CallSubjectSummary FROM dbo.IndividualCallAnalyses WHERE AgentID = ? AND "
        params = [agent_id]

        if processing_date_time is None:
            calls_query += "ProcessingDateTime IS NULL"
        else:
            calls_query += "ProcessingDateTime = ?"
            params.append(processing_date_time)
        
        calls_query += " ORDER BY CallDateTime;"

        cursor.execute(calls_query, params)
        
        columns = [column[0] for column in cursor.description]
        calls = [dict(zip(columns, row)) for row in cursor.fetchall()]
        details['calls'] = calls
        
        conn.close()
        return details
    except Exception as ex:
        print(f"--- !!! DATABASE ERROR IN phone_qa_db.py (get_details_for_combined_analysis) !!! ---")
        print(f"Error Type: {type(ex).__name__}")
        print(f"Error Details: {ex}")
        print("--- END DATABASE ERROR ---")
        raise

def get_individual_call_details(analysis_id):
    """
    Fetches all details for a single individual call analysis using the corrected schema.
    """
    try:
        conn = get_phone_qa_db_connection()
        cursor = conn.cursor()
        details = {}
        
        print(f"\n--- DEBUG: Fetching details for INDIVIDUAL analysis ID: {analysis_id} ---")
        
        header_query = """
            SELECT ica.AnalysisID, ica.AgentID, ag.AgentName, ica.OriginalAudioFileName, ica.CallDateTime, ica.CallSubjectSummary
            FROM dbo.IndividualCallAnalyses ica
            JOIN dbo.Agents ag ON ica.AgentID = ag.AgentID
            WHERE ica.AnalysisID = ?
        """
        cursor.execute(header_query, analysis_id)
        header_row = cursor.fetchone()
        if not header_row:
            conn.close()
            return {"error": "Individual call analysis not found."}
        
        columns = [column[0] for column in cursor.description]
        details['header'] = dict(zip(columns, header_row))
        print("--- DEBUG: Individual header found. ---")

        details_query = """
            SELECT 
                iei.EvaluationItemID,
                qpm.Category AS FindingCategory,
                qpm.QualityPointText AS FindingText,
                iei.Finding AS FindingType,
                iei.ExplanationSnippets
            FROM 
                dbo.IndividualEvaluationItems AS iei
            JOIN 
                dbo.QualityPointsMaster AS qpm ON iei.QualityPointID = qpm.QualityPointID
            WHERE 
                iei.AnalysisID = ?
            ORDER BY 
                qpm.Category;
        """
        print(f"--- DEBUG: Executing individual findings query... ---")
        cursor.execute(details_query, analysis_id)
        columns = [column[0] for column in cursor.description]
        details['findings'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        print(f"--- DEBUG: Found {len(details['findings'])} individual findings. ---")

        conn.close()
        return details
    except Exception as ex:
        print(f"--- !!! DATABASE ERROR IN get_individual_call_details !!! ---")
        print(f"Error Type: {type(ex).__name__}")
        print(f"Error Details: {ex}")
        print("--- END DATABASE ERROR ---")
        raise

def get_agent_by_id(agent_id):
    """Fetches a single agent's name by their ID."""
    conn = get_phone_qa_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT AgentName FROM dbo.Agents WHERE AgentID = ?", agent_id)
    row = cursor.fetchone()
    conn.close()
    return row.AgentName if row else None
