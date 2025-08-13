Of course. A good README file is essential for any project.

While you requested a `.doc` file, the standard for code repositories like GitHub is a Markdown file named **`README.md`**. It's a plain text format that renders beautifully on sites like GitHub, making it easy to read and maintain. I will generate the content in this standard format for you.

Here is a comprehensive `README.md` for your project, created by reviewing all the files and information you've provided.

-----

# QA & Performance Analysis Hub

An integrated Flask-based web application designed for quality assurance and performance analysis in an IT support environment. This hub provides a suite of tools for reviewing help desk tickets, analyzing technician performance with detailed metrics, and leveraging AI for documentation and call quality analysis.

## Screenshots

| Landing Hub | Performance Scorecard | Review Worklist |
| :---: | :---: | :---: |
|  |  |  |

## Features

  * **Central Hub**: A main landing page providing access to all tools.
  * **Ticket QA System**:
      * Conduct new, detailed quality reviews on ConnectWise tickets using customizable profiles.
      * View historical ticket QA reports with dynamic filtering.
      * Find and edit previously submitted reviews.
  * **QA Review Worklist**: A prioritized list showing which technicians are due for a review based on their last review date.
  * **Performance Scorecard**:
      * View detailed, aggregated statistics for technicians, including hours, tickets, and call data.
      * Select dynamic timeframes (monthly, weekly, daily) to analyze performance trends.
      * Interactive chart to plot and compare different metrics over time.
      * Download table data as a CSV file.
  * **AI-Powered Analysis**:
      * Generate a natural language performance summary and compliance check on the scorecard page.
      * Run in-depth documentation quality analysis on a strategic sample of a technician's tickets.
  * **Phone System Tools**:
      * View reports on AI-driven phone call QA.
      * Process local audio files for transcription or on-demand QA analysis.

## Technology Stack

  * **Backend**: Python, Flask
  * **Database**: Microsoft SQL Server (connects to multiple databases for ConnectWise, Ticket QA, and Phone Call data)
  * **Frontend**: HTML, Bootstrap 5, JavaScript, Chart.js
  * **AI & Machine Learning**:
      * **LLM Service**: Ollama for local model hosting
      * **Transcription**: OpenAI Whisper
      * **Speaker Diarization**: Pyannote Audio
      * **Cloud AI**: Google Gemini (for on-demand audio file QA)

-----

## Setup and Installation

### Prerequisites

  * Python 3.x
  * Pip (Python package installer)
  * Microsoft ODBC Driver for SQL Server
  * [Ollama](https://ollama.com/) installed and running with the required models pulled (e.g., `ollama pull llama3.1:8b`)

### Installation Steps

1.  Clone the repository to your local machine or server.
2.  Navigate to the project directory in your terminal.
3.  Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

### Configuration

All application settings are managed in the **`Config.ini`** file. You must update this file with your specific database credentials, server paths, and AI model names.

  * **`[Database]`**: Connection details for your primary QA database (where ticket reviews are stored).
  * **`[ConnectWiseDB]`**: Connection details for your ConnectWise database, used for fetching member and ticket data.
  * **`[CallDataDB]`**: Connection details for your 3CX phone system database (`GlobalTechSolutions3CXData`).
  * **`[PhoneQADatabase]`**: Connection details for the separate Phone Call QA database.
  * **`[Email]`**: SMTP server settings for sending email reports.
  * **`[ScoreCardAI]`**: Settings for the scorecard's AI analysis, including the Ollama host URL and the model name.
  * **`[TicketAnalysisAI]`**: Settings for the standalone ticket documentation analyzer, including model name and prompt paths.
  * **`[API]`**: Contains the Google API key for the on-demand audio file QA.
  * **`[Prompts]`**: File paths for the various AI prompt templates used by the application.

-----

## Running the Application

### Development

For local development and testing, you can run the application directly from the command line:

```sh
python app.py
```

The application will be accessible at `http://127.0.0.1:5000`.

### Production

The application is configured to run on a production server using IIS and wfastcgi. Ensure your `web.config` file is correctly set up to point to your Python installation and the `app.py` file. Any changes to configuration or Python files will require an **IIS Application Pool Recycle** to take effect.

## Key Modules

  * **`app.py`**: The main Flask application. Defines all URL routes and API endpoints.
  * **`database.py`**: Handles all database connections and queries for the Ticket QA and ConnectWise systems.
  * **`phone_qa_db.py`**: Handles all database connections and queries for the Phone Call QA system.
  * **`tech_scorecard.py`**: A class that orchestrates the data collection and aggregation for the Performance Scorecard page.
  * **`ticket_analyzer.py`**: Contains the logic for the AI-powered ticket documentation analysis feature.
  * **`call_processor.py`**: Contains the logic for transcribing and analyzing audio files.
  * **`config_manager.py`**: A simple utility for reading settings from `Config.ini`.
