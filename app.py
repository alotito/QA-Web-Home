import os
import base64

# --- IIS PERMISSIONS FIX ---
# This block MUST be the very first piece of executable code to run.
# It defines a local cache directory and sets environment variables
# BEFORE any other libraries that use a cache (like torch or pyannote) are imported.

# 1. Define a local cache directory within the application folder.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models_cache')
if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
        print(f"Created local cache directory: {CACHE_DIR}")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not create cache directory at {CACHE_DIR}. Error: {e}")

# 2. Set environment variables to force libraries to use our local cache.
os.environ['HF_HOME'] = CACHE_DIR
os.environ['PYANNOTE_CACHE'] = CACHE_DIR
os.environ['TORCH_HOME'] = CACHE_DIR
print(f"Set HF_HOME, PYANNOTE_CACHE, and TORCH_HOME to: {CACHE_DIR}")


# Now that the environment is configured, we can safely import the rest of our application.
from flask import Flask, render_template, jsonify, request, send_from_directory, session
import uuid
from datetime import datetime, timedelta
import database as db
import email_service as email
import phone_qa_db as phone_db
import call_processor
from config_manager import get_config
from werkzeug.utils import secure_filename

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure a temporary folder for file uploads
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Add a context processor to make the 'now' function available in all templates
@app.context_processor
def inject_now():
    """Makes the 'now' function available in all Jinja2 templates."""
    return {'now': datetime.now}

# --- Main and Ticket QA System Routes ---
@app.route('/')
def landing_page():
    return render_template('landing.html')

@app.route('/new_review')
def new_review():
    try:
        tech_id_to_select = request.args.get('tech_id', type=int)
        profiles = db.get_active_profiles()
        members = db.get_all_members()
        return render_template('index.html', profiles=profiles, members=members, selected_tech_id=tech_id_to_select)
    except Exception as e:
        app.logger.error(f"Error loading new review page: {e}")
        return render_template('error.html', error_message=str(e)), 500

@app.route('/reports')
def reports():
    try:
        profiles = db.get_active_profiles()
        members = db.get_all_members()
        return render_template('reports.html', profiles=profiles, members=members)
    except Exception as e:
        app.logger.error(f"Error loading reports page: {e}")
        return render_template('error.html', error_message=str(e)), 500

@app.route('/worklist')
def worklist():
    try:
        worklist_data = db.get_tech_review_worklist()
        return render_template('worklist.html', worklist_data=worklist_data)
    except Exception as e:
        app.logger.error(f"Error loading worklist page: {e}")
        return render_template('error.html', error_message=str(e)), 500

@app.route('/print_review/<string:review_id>')
def print_review(review_id):
    try:
        review_data = db.get_review_by_id(review_id)
        if not review_data:
            return "Review not found", 404
        return render_template('printable_review.html', header=review_data[0], answers=review_data)
    except Exception as e:
        app.logger.error(f"Error loading print page for review {review_id}: {e}")
        return render_template('error.html', error_message=str(e)), 500


# --- Ticket QA System API Routes ---
@app.route('/get_questions/<int:profile_id>')
def get_questions(profile_id):
    try:
        questions = db.get_profile_questions(profile_id)
        return jsonify(questions)
    except Exception as e:
        app.logger.error(f"Error fetching questions for profile {profile_id}: {e}")
        return jsonify({"error": "Failed to fetch questions.", "details": str(e)}), 500

@app.route('/get_report_data', methods=['POST'])
def get_report_data():
    try:
        filters = request.json
        report_data = db.get_filtered_reviews(filters)
        return jsonify(report_data)
    except Exception as e:
        app.logger.error(f"Error fetching report data: {e}")
        return jsonify({"error": "Failed to fetch report data.", "details": str(e)}), 500

@app.route('/save_review', methods=['POST'])
def save_review():
    review_data = request.json
    do_not_save = review_data.get('do_not_save', False)
    total_score = sum(float(a.get('score', 0)) for a in review_data.get('answers', []))
    max_score = sum(float(a.get('max_points', 0)) for a in review_data.get('answers', []))
    final_percentage = (total_score / max_score) if max_score > 0 else 0
    
    if not do_not_save:
        try:
            review_id = uuid.uuid4()
            db.save_review_to_db(
                review_id=review_id, date_executed=datetime.now(),
                executed_by=review_data.get('reviewer_name', 'System'),
                member_rec_id=review_data.get('technician_id'),
                member_full_name=review_data.get('technician_name'),
                profile_id=review_data.get('profile_id'), score=final_percentage,
                comment=review_data.get('overall_comment'),
                ticket_nbr=review_data.get('ticket_number'),
                answers=review_data.get('answers')
            )
        except Exception as e:
            app.logger.error(f"DATABASE SAVE FAILED: {e}")
            return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    
    try:
        html_report = email.generate_html_report(review_data)
        subject = f"QA Review for {review_data['technician_name']} - Ticket #{review_data['ticket_number']}"
        to_address = review_data['email_to']
        cc_addresses = review_data['email_cc']
        success, message = email.send_review_email(to_address, cc_addresses, subject, html_report)
        if not success:
            raise Exception(message)
    except Exception as e:
        app.logger.error(f"EMAIL FAILED: {e}")
        msg = "Review saved to DB, but email failed." if not do_not_save else f"Email failed: {e}"
        return jsonify({"success": False, "message": msg}), 500

    success_message = "Review saved and email sent successfully!" if not do_not_save else "Email sent successfully (not saved to DB)."
    return jsonify({"success": True, "message": success_message})


# --- Automated Phone QA System Routes & APIs ---
@app.route('/phone_qa_status')
def phone_qa_status():
    try:
        latest_run = phone_db.get_latest_run_status()
        return render_template('phone_qa_status.html', latest_run=latest_run)
    except Exception as e:
        return render_template('error.html', error_message=str(e)), 500

@app.route('/phone_qa_reports')
def phone_qa_reports():
    try:
        agents = phone_db.get_all_phone_agents()
        return render_template('phone_qa_reports.html', agents=agents)
    except Exception as e:
        return render_template('error.html', error_message=str(e)), 500

@app.route('/get_phone_report_data', methods=['POST'])
def get_phone_report_data():
    try:
        filters = request.json
        report_data = phone_db.get_combined_analyses_by_filter(filters)
        return jsonify(report_data)
    except Exception as e:
        app.logger.error(f"Error fetching phone report data: {e}")
        return jsonify({"error": "Failed to fetch report data.", "details": str(e)}), 500

@app.route('/get_phone_report_details/<int:analysis_id>')
def get_phone_report_details(analysis_id):
    try:
        details = phone_db.get_details_for_combined_analysis(analysis_id)
        return jsonify(details)
    except Exception as e:
        app.logger.error(f"Error fetching phone report details for ID {analysis_id}: {e}")
        return jsonify({"error": "Failed to fetch report details.", "details": str(e)}), 500

@app.route('/get_individual_call_details/<int:analysis_id>')
def get_individual_call_details(analysis_id):
    try:
        details = phone_db.get_individual_call_details(analysis_id)
        return jsonify(details)
    except Exception as e:
        app.logger.error(f"Error fetching individual call details for ID {analysis_id}: {e}")
        return jsonify({"error": "Failed to fetch individual call details.", "details": str(e)}), 500

@app.route('/print_phone_report/combined/<int:analysis_id>')
def print_phone_combined(analysis_id):
    try:
        details = phone_db.get_details_for_combined_analysis(analysis_id)
        return render_template('printable_phone_combined.html', details=details)
    except Exception as e:
        return render_template('error.html', error_message=str(e)), 500

@app.route('/print_phone_report/individual/<int:analysis_id>')
def print_phone_individual(analysis_id):
    try:
        details = phone_db.get_individual_call_details(analysis_id)
        return render_template('printable_phone_individual.html', details=details)
    except Exception as e:
        return render_template('error.html', error_message=str(e)), 500


# --- File Tools Routes & APIs ---
@app.route('/file_tools')
def file_tools():
    return render_template('file_tools.html')

@app.route('/api/transcribe_upload', methods=['POST'])
def transcribe_upload():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(temp_path)
            transcript = call_processor.transcribe_audio(temp_path)
            return jsonify({'transcript': transcript})
        except Exception as e:
            app.logger.error(f"Error during file upload/transcription: {e}")
            return jsonify({'error': str(e)}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

@app.route('/api/qa_audio_upload', methods=['POST'])
def qa_audio_upload():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400

    if file:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(temp_path)
            qa_report_data = call_processor.qa_audio(temp_path)
            if 'error' in qa_report_data:
                return jsonify(qa_report_data), 500
            session['last_qa_report'] = qa_report_data
            return jsonify({'success': True, 'message': 'Analysis complete. Report is ready.'})
        except Exception as e:
            app.logger.error(f"Error during QA audio upload/analysis: {e}")
            return jsonify({'error': str(e)}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

@app.route('/print_manual_qa')
def print_manual_qa():
    report_data = session.get('last_qa_report')
    if not report_data:
        return "No QA report found in session. Please generate a report first.", 404
    return render_template('printable_manual_qa_report.html', report_data=report_data)


# --- Main Execution ---
if __name__ == '__main__':
    # The secret key is now set globally above
    app.run(debug=True)
