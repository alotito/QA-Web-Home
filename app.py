from flask import Flask, render_template, jsonify, request
import database as db
import email_service as email
import uuid
from datetime import datetime
import phone_qa_db as phone_db

# Initialize the Flask application
app = Flask(__name__)

# Add a context processor to make datetime available in all templates
@app.context_processor
def inject_now():
    """Makes the 'now' function available in all Jinja2 templates."""
    return {'now': datetime.now}

# --- Ticket QA System Routes ---

@app.route('/')
def landing_page():
    """Renders the main landing page."""
    return render_template('landing.html')

@app.route('/new_review')
def new_review():
    """Renders the page for creating a new review."""
    try:
        tech_id_to_select = request.args.get('tech_id', type=int)
        profiles = db.get_active_profiles()
        members = db.get_all_members()
        return render_template('index.html', profiles=profiles, members=members, selected_tech_id=tech_id_to_select)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading new review page: {error_message}")
        return render_template('error.html', error_message=error_message), 500

@app.route('/reports')
def reports():
    """Renders the main page for viewing ticket reports."""
    try:
        profiles = db.get_active_profiles()
        members = db.get_all_members()
        return render_template('reports.html', profiles=profiles, members=members)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading reports page: {error_message}")
        return render_template('error.html', error_message=error_message), 500

@app.route('/worklist')
def worklist():
    """Renders the page that shows which technicians are due for a review."""
    try:
        worklist_data = db.get_tech_review_worklist()
        return render_template('worklist.html', worklist_data=worklist_data)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading worklist page: {error_message}")
        return render_template('error.html', error_message=error_message), 500

@app.route('/print_review/<string:review_id>')
def print_review(review_id):
    """Renders a printer-friendly page for a single ticket review."""
    try:
        review_data = db.get_review_by_id(review_id)
        if not review_data:
            return "Review not found", 404
        header = review_data[0]
        answers = review_data
        return render_template('printable_review.html', header=header, answers=answers)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading print page for review {review_id}: {error_message}")
        return render_template('error.html', error_message=error_message), 500

# --- Ticket QA System API Routes ---

@app.route('/get_questions/<int:profile_id>')
def get_questions(profile_id):
    """API endpoint to get all questions for a specific profile ID."""
    try:
        questions = db.get_profile_questions(profile_id)
        return jsonify(questions)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error fetching questions for profile {profile_id}: {error_message}")
        return jsonify({"error": "Failed to fetch questions from the database.", "details": error_message}), 500

@app.route('/get_report_data', methods=['POST'])
def get_report_data():
    """API endpoint to fetch filtered ticket review data."""
    try:
        filters = request.json
        report_data = db.get_filtered_reviews(filters)
        return jsonify(report_data)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error fetching report data: {error_message}")
        return jsonify({"error": "Failed to fetch report data.", "details": error_message}), 500

@app.route('/save_review', methods=['POST'])
def save_review():
    """API endpoint to save the completed review and/or send the email."""
    review_data = request.json
    do_not_save = review_data.get('do_not_save', False)
    total_score = 0
    max_score = 0
    for answer in review_data.get('answers', []):
        total_score += float(answer.get('score', 0))
        max_score += float(answer.get('max_points', 0))
    final_percentage = (total_score / max_score) if max_score > 0 else 0
    if not do_not_save:
        try:
            review_id = uuid.uuid4()
            db.save_review_to_db(
                review_id=review_id,
                date_executed=datetime.now(),
                executed_by=review_data.get('reviewer_name', 'System'),
                member_rec_id=review_data.get('technician_id'),
                member_full_name=review_data.get('technician_name'),
                profile_id=review_data.get('profile_id'),
                score=final_percentage,
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
            email_error_message = f"Email failed: {message}"
            if not do_not_save:
                email_error_message = "Review saved to DB, but " + email_error_message
            return jsonify({"success": False, "message": email_error_message}), 500
    except Exception as e:
        app.logger.error(f"EMAIL PREPARATION FAILED: {e}")
        email_error_message = f"Email preparation failed: {e}"
        if not do_not_save:
            email_error_message = "Review saved to DB, but " + email_error_message
        return jsonify({"success": False, "message": email_error_message}), 500
    if do_not_save:
        success_message = "Review sent via email successfully (not saved to DB)."
    else:
        success_message = "Review saved and email sent successfully!"
    return jsonify({"success": True, "message": success_message})

# --- Automated Phone QA System Routes ---

@app.route('/phone_qa_status')
def phone_qa_status():
    """Renders the status page for the Automated Phone QA system."""
    try:
        latest_run = phone_db.get_latest_run_status()
        return render_template('phone_qa_status.html', latest_run=latest_run)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading Phone QA Status page: {error_message}")
        return render_template('error.html', error_message=error_message), 500

@app.route('/phone_qa_reports')
def phone_qa_reports():
    """Renders the main page for viewing phone QA reports."""
    try:
        agents = phone_db.get_all_phone_agents()
        return render_template('phone_qa_reports.html', agents=agents)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error loading Phone QA Reports page: {error_message}")
        return render_template('error.html', error_message=error_message), 500

# --- NEW PRINT ROUTES ADDED HERE ---
@app.route('/print_phone_report/combined/<int:analysis_id>')
def print_phone_combined(analysis_id):
    """Renders a printer-friendly page for a combined phone analysis report."""
    try:
        details = phone_db.get_details_for_combined_analysis(analysis_id)
        if not details or 'error' in details:
            return "Combined analysis report not found.", 404
        return render_template('printable_phone_combined.html', details=details)
    except Exception as e:
        app.logger.error(f"Error loading print page for combined report {analysis_id}: {e}")
        return render_template('error.html', error_message=str(e)), 500

@app.route('/print_phone_report/individual/<int:analysis_id>')
def print_phone_individual(analysis_id):
    """Renders a printer-friendly page for an individual call analysis."""
    try:
        details = phone_db.get_individual_call_details(analysis_id)
        if not details or 'error' in details:
            return "Individual call report not found.", 404
        return render_template('printable_phone_individual.html', details=details)
    except Exception as e:
        app.logger.error(f"Error loading print page for individual call {analysis_id}: {e}")
        return render_template('error.html', error_message=str(e)), 500

# --- Automated Phone QA System API Routes ---

@app.route('/get_phone_report_data', methods=['POST'])
def get_phone_report_data():
    """API endpoint to fetch filtered phone review data."""
    try:
        filters = request.json
        report_data = phone_db.get_combined_analyses_by_filter(filters)
        return jsonify(report_data)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error fetching phone report data: {error_message}")
        return jsonify({"error": "Failed to fetch report data.", "details": error_message}), 500

@app.route('/get_phone_report_details/<int:analysis_id>')
def get_phone_report_details(analysis_id):
    """API endpoint to fetch the detailed breakdown of a combined analysis."""
    try:
        details = phone_db.get_details_for_combined_analysis(analysis_id)
        if not details or 'error' in details:
            return jsonify({"error": "No details found for this analysis ID."}), 404
        return jsonify(details)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error fetching phone report details for ID {analysis_id}: {error_message}")
        return jsonify({"error": "Failed to fetch report details.", "details": error_message}), 500

@app.route('/get_individual_call_details/<int:analysis_id>')
def get_individual_call_details(analysis_id):
    """API endpoint to fetch details for a single analyzed call."""
    try:
        details = phone_db.get_individual_call_details(analysis_id)
        if "error" in details:
            return jsonify(details), 404
        return jsonify(details)
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"Error fetching individual call details for ID {analysis_id}: {error_message}")
        return jsonify({"error": "Failed to fetch individual call details.", "details": error_message}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)
