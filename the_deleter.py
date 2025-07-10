from flask import Flask, render_template, jsonify, request
import database as db

# This is a separate Flask application for the deletion tool.
app = Flask(__name__)

@app.route('/')
def index():
    """Renders the main page for the review deletion tool."""
    try:
        # Get the list of technicians to populate the search filter
        members = db.get_all_members()
        return render_template('the_deleter.html', members=members)
    except Exception as e:
        # If the database connection fails, render an error message
        print(f"ERROR loading deleter tool: {e}")
        return f"<h1>Database Connection Error</h1><p>Could not connect to the database to fetch technicians. Please ensure the main application is working and the config is correct.</p><p><strong>Error:</strong> {e}</p>"

@app.route('/api/search_reviews', methods=['POST'])
def search_reviews():
    """API endpoint to search for reviews based on filters."""
    try:
        filters = request.json
        # We can reuse the existing function from database.py
        reviews = db.get_filtered_reviews(filters)
        return jsonify(reviews)
    except Exception as e:
        print(f"ERROR searching reviews: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete_review', methods=['POST'])
def delete_review():
    """API endpoint to delete a specific review by its ID."""
    try:
        data = request.json
        review_id = data.get('review_id')
        if not review_id:
            return jsonify({"success": False, "message": "Review ID is required."}), 400

        # Call the new delete function in the database module
        success = db.delete_review_by_id(review_id)

        if success:
            return jsonify({"success": True, "message": f"Review {review_id} was deleted successfully."})
        else:
            return jsonify({"success": False, "message": f"Review {review_id} not found or could not be deleted."}), 404
            
    except Exception as e:
        print(f"ERROR deleting review: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("--- Starting Review Deletion Tool ---")
    print("--- WARNING: This is a destructive tool. Use with extreme caution. ---")
    # Running on port 5001 to avoid conflicts with the main QA app (which runs on 5000)
    app.run(debug=True, port=5001)
