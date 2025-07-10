QA Review Application
Version: 1.1.0
Author: Albert L., Service Delivery Manager, Global Tech Solutions LLC

Overview
The QA Review Application is a comprehensive, web-based tool designed to streamline and enhance the quality assurance processes at Global Tech Solutions. Built with Python and the Flask framework, it provides a robust platform for two key QA functions: manual ticket reviews and automated phone call analysis reporting.

This application now features a sophisticated multi-database architecture, connecting to the local GTS-QADB for review data, the PhoneQA database for call analysis, and the live cwwebapp_globaltsllc (ConnectWise) database to serve as the single source of truth for all technician information.

Key Features
1. Ticket QA System
Live Technician Data: Pulls the list of all active technicians directly from the ConnectWise database, ensuring the list is always up-to-date.

Dynamic Review Forms: Load different sets of questions (QA Profiles) based on the type of ticket being reviewed.

Scoring and Feedback: Score technicians on each question and provide specific observations.

Automated Email Reports: Automatically generate and send detailed HTML-formatted reports of the review to the technician and relevant managers.

Historical Reporting: Filter and view past reviews by technician, date range, or QA profile.

Technician Worklist: Quickly see which technicians are due for a review based on the date of their last one, cross-referencing live data from ConnectWise.

2. Automated Phone QA System
System Status: Check the status of the last automated analysis run to ensure the system is processing calls correctly.

Multi-Level Drill-Down Reporting: View high-level analysis reports for each agent, drill down into the specific calls that contributed to the summary, and then drill down again to see the detailed findings for each individual call.

Printable Reports: Generate clean, printer-friendly versions of both the combined analysis reports and the individual call detail reports.

Data Filtering: Easily filter reports by agent and date range to focus on specific performance periods.

3. Administrative Tools
Review Deletion Utility: A separate, standalone web application (the_deleter.py) allows authorized users to search for and permanently delete test reviews or erroneous entries from the database, keeping it separate from the main user-facing application for safety.

Project Structure
.
├── app.py                      # Main Flask application for QA reviews
├── the_deleter.py              # Standalone Flask app for deleting reviews
├── database.py                 # Handles DB logic for the Ticket QA system and ConnectWise
├── phone_qa_db.py              # Handles DB logic for the Phone QA system
├── email_service.py            # Generates and sends HTML emails
├── config_manager.py           # Reads settings from Config.ini
├── Config.ini                  # Configuration file for all database and email settings
├── requirements.txt            # Lists all Python package dependencies
└── templates/
    ├── index.html              # Page for creating a new ticket review
    ├── reports.html            # Page for viewing historical ticket reviews
    ├── worklist.html           # Page for the technician review worklist
    ├── phone_qa_reports.html   # Page for viewing phone call analysis reports
    ├── phone_qa_status.html    # Page to show the status of the automated system
    ├── landing.html            # The main home/navigation page
    ├── the_deleter.html        # Interface for the review deletion tool
    ├── printable_review.html   # Print template for a ticket review
    ├── printable_phone_combined.html  # Print template for a combined phone report
    └── printable_phone_individual.html # Print template for an individual call report

Setup and Installation
Prerequisites
Python 3.6+

pip (Python package installer)

Microsoft ODBC Driver 17 for SQL Server

Installation Steps
Clone the Repository

git clone <your-github-repository-url>
cd qa-review-app

Create and Activate a Virtual Environment

Windows:

python -m venv venv
.\venv\Scripts\activate

macOS/Linux:

python3 -m venv venv
source venv/bin/activate

Install Dependencies
If it doesn't exist, create a requirements.txt file with the following content:

Flask
pyodbc

Then, install the packages:

pip install -r requirements.txt

Configure Config.ini
Open Config.ini and ensure all four sections are correctly filled out for your environment:

[Database]: Credentials for the primary GTS-QADB database.

[PhoneQADatabase]: Credentials for the PhoneQA database.

[ConnectWiseDB]: Credentials for the cwwebapp_globaltsllc database. The user for this database only needs read permissions.

[Email]: Your SMTP server settings.

Database Permissions Setup
For the application to function correctly, the QAReviewer user requires specific permissions on the SQL Server instance.

The login QAReviewer must exist on the GTSTCH-CWR01 server.

The server must be configured for "SQL Server and Windows Authentication mode" (Mixed Mode).

The QAReviewer user must be mapped to the GTS-QADB database with read/write permissions (or permissions to execute the stored procedure).

The QAReviewer user must be mapped to the cwwebapp_globaltsllc database with at least db_datareader permissions to allow it to read the technician list.

Usage
The project contains two separate applications.

Main QA Application
To run the main application for reviewing tickets and viewing reports:

flask run

The application will be available at http://127.0.0.1:5000.

Review Deletion Tool
To run the administrative tool for deleting test reviews:

python the_deleter.py

This tool runs on a different port to avoid conflicts and will be available at http://127.0.0.1:5001.
