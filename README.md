QA Review Application
Version: 2.0.0
Author: Albert L., Service Delivery Manager, Global Tech Solutions LLC

1. Overview
The QA Review Application is a comprehensive, enterprise-grade web platform designed to centralize and enhance the quality assurance processes at Global Tech Solutions. Built with Python and the Flask framework, this application provides a suite of tools for both manual and automated QA tasks, leveraging local AI models for transcription and diarization, and cloud AI for analysis.

The system is built on a multi-database architecture, connecting to the local GTS-QADB for ticket review data, the PhoneQA database for historical call analysis, and the live cwwebapp_globaltsllc (ConnectWise) database, which serves as the single source of truth for all technician and agent information.

2. Core Modules & Functionality
The application is composed of several distinct modules, each with a specific purpose:

File / Module

Function

app.py

The main Flask web application. It serves all user-facing pages and API endpoints for the Ticket QA, Phone QA, and File Tools modules.

database.py

Handles all database logic for the Ticket QA System. It connects to both the local GTS-QADB and the cwwebapp_globaltsllc database to fetch data and save reviews.

phone_qa_db.py

Manages all database interactions for the Automated Phone QA System, connecting to the PhoneQA database to retrieve historical analysis reports.

call_processor.py

The core AI engine. It handles the complex tasks of audio transcription and speaker diarization using local, GPU-accelerated models (whisper, pyannote.audio) and sends audio to the Google Gemini API for analysis.

config_manager.py

A simple, robust utility for reading all settings (database credentials, API keys, paths) from the central Config.ini file.

email_service.py

Generates and sends HTML-formatted ticket review emails via an SMTP server.

the_deleter.py

A separate, standalone Flask application for administrative use. It provides a safe interface to delete test data or erroneous reviews without exposing this functionality in the main application.

3. Features
Ticket QA System
Live Technician Data: Pulls the list of all active technicians directly from the ConnectWise database, ensuring the list is always up-to-date.

Dynamic Review Forms: Loads different sets of questions (QA Profiles) based on the type of ticket being reviewed.

Automated Email Reports: Generates and sends detailed HTML-formatted reports of the review.

Historical Reporting & Worklist: Provides tools to view past reviews and see which technicians are due for a review.

Automated Phone QA System
Drill-Down Reporting: View high-level analysis reports for each agent, drill down into the specific calls that contributed to the summary, and then drill down again to see the detailed findings for each individual call.

Printable Reports: Generates clean, printer-friendly versions of both combined and individual call reports.

On-Demand File Tools
Local File Transcription: Allows a user to upload a local audio file (.wav, .mp3, etc.) and receive a complete, speaker-diarized transcript in SRT format.

Local File QA: Allows a user to upload a local audio file to be sent directly to the Google Gemini model for a full QA analysis, with the results formatted into a printable HTML report.

4. System & Software Dependencies
Properly configuring the server environment is critical for this application to function, especially when deploying under IIS.

a) Python & Libraries
The application requires Python 3.x and the libraries listed in requirements.txt.

# requirements.txt
Flask
pyodbc
openai-whisper
google-generativeai
ffmpeg-python
pyannote.audio
torch
torchaudio
soundfile

b) NVIDIA GPU & CUDA (Highly Recommended)
For acceptable performance of the transcription and diarization features, the server must have an NVIDIA GPU.

The appropriate NVIDIA drivers must be installed.

The NVIDIA CUDA Toolkit must be installed. The version should be determined by running nvidia-smi on the server.

The torch and torchaudio Python libraries must be installed using the specific command from the PyTorch website that matches the server's CUDA version to enable GPU acceleration.

c) FFmpeg
The ffmpeg command-line tool is a critical dependency for the audio processing libraries.

It must be downloaded from ffmpeg.org and installed on the server.

The location of the ffmpeg.exe file (usually in a bin folder) must be added to the system's PATH environment variable.

d) Microsoft C++ Build Tools
To install the pyannote.audio library and its dependencies on Windows, the Microsoft C++ Build Tools are required.

They can be downloaded from the Visual Studio website.

During installation, the "Desktop development with C++" workload must be selected.

5. IIS Deployment Configuration
Deploying this application under IIS requires several non-default configurations.

a) Application Pool Identity
The application cannot run under the default ApplicationPoolIdentity.

The Application Pool must be configured to run as a Custom account.

This account should ideally be a dedicated domain service account (e.g., DOMAIN\svc_QAReviewer) that has been granted the necessary permissions.

b) Server & Network Permissions
The account running the Application Pool needs the following permissions:

On the Web Server: It must be granted the "Log on as a batch job" right in the Local Security Policy (secpol.msc).

On the Network Share: It must have Read permissions on the call recording folder (e.g., \\gts-3cx2016-az\recordings).

On the Application Folders: It must have Modify permissions on the uploads and models_cache subfolders within the main application directory (C:\inetpub\wwwroot\qa_review_app\) to allow it to save temporary files and download AI models.

c) web.config
A web.config file is required in the root of the application directory to interface with IIS.

<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI" 
           path="*" 
           verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\inetpub\wwwroot\qa_review_app\venv\Scripts\python.exe|C:\inetpub\wwwroot\qa_review_app\venv\Lib\site-packages\wfastcgi.py" 
           resourceType="Unspecified" 
           requireAccess="Script" />
    </handlers>
  </system.webServer>

  <appSettings>
    <!-- Points to your Flask app object: <filename>.<app_object_name> -->
    <add key="WSGI_HANDLER" value="app.app" />
    
    <!-- The root of your application -->
    <add key="PYTHONPATH" value="C:\inetpub\wwwroot\qa_review_app" />
    
    <!-- Optional: A log file for wfastcgi debugging -->
    <add key="WSGI_LOG" value="C:\inetpub\wwwroot\qa_review_app\wfastcgi.log" />
  </appSettings>
</configuration>

6. Usage
Main QA Application
To run the main application for development purposes:

# Navigate to the project directory
cd C:\inetpub\wwwroot\qa_review_app
# Activate the virtual environment
venv\Scripts\activate
# Run the app
python app.py

The application will be available at http://127.0.0.1:5000.

Review Deletion Tool
To run the administrative tool for deleting test reviews:

# Navigate to the project directory
cd C:\inetpub\wwwroot\qa_review_app
# Activate the virtual environment
venv\Scripts\activate
# Run the deleter app
python the_deleter.py

This tool runs on a different port and will be available at http://127.0.0.1:5001.
