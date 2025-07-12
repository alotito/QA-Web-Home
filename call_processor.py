import os
import json
import base64
import shutil

# --- LOCAL CACHE SETUP ---
# Define a local cache directory within the application folder.
# This ensures the IIS user has permission to write model files.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models_cache')
if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
        print(f"Created local cache directory: {CACHE_DIR}")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not create cache directory at {CACHE_DIR}. Error: {e}")

# Now we can import the libraries
import whisper
import google.generativeai as genai
from config_manager import get_config
import ffmpeg
import numpy as np
import torch
from pyannote.audio import Pipeline

# --- Global Initialization ---
try:
    hf_token = get_config('HuggingFace', 'AccessToken')
    # --- EXPLICIT CACHE PATH ---
    # Directly tell the pipeline where to save its models.
    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
        cache_dir=CACHE_DIR
    )
    if torch.cuda.is_available():
        print("Moving diarization pipeline to GPU.")
        diarization_pipeline.to(torch.device("cuda"))
    print("Diarization pipeline loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load diarization pipeline. Diarization will not work. Error: {e}")
    diarization_pipeline = None


def transcribe_audio(file_path):
    """
    Transcribes an audio file using Whisper and adds speaker labels
    using Pyannote's diarization model.
    """
    if not diarization_pipeline:
        return "Error: Speaker diarization pipeline is not available. Please check server logs."

    print("--- Starting Transcription and Diarization ---")
    try:
        # 1. Run Speaker Diarization
        print("Step 1: Running speaker diarization...")
        diarization = diarization_pipeline(file_path)
        print("Diarization complete.")

        # 2. Run Transcription
        print("Step 2: Loading Whisper model and running transcription...")
        # --- EXPLICIT CACHE PATH ---
        # Directly tell Whisper where to save its models.
        model = whisper.load_model("tiny", download_root=CACHE_DIR)
        transcription_result = model.transcribe(file_path)
        print("Transcription complete.")

        # 3. Align Transcription with Diarization
        print("Step 3: Aligning transcription with speaker turns...")
        final_segments = []
        for segment in transcription_result["segments"]:
            speaker = "UNKNOWN"
            for turn, _, speaker_label in diarization.itertracks(yield_label=True):
                if turn.start <= segment['start'] <= turn.end or segment['start'] <= turn.start <= segment['end']:
                    speaker = speaker_label
                    break
            
            final_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "speaker": speaker
            })
        print("Alignment complete.")

        def format_timestamp(seconds):
            assert seconds >= 0, "non-negative timestamp expected"
            milliseconds = round(seconds * 1000.0)
            hours = int(milliseconds // 3_600_000); milliseconds %= 3_600_000
            minutes = int(milliseconds // 60_000); milliseconds %= 60_000
            seconds = int(milliseconds // 1_000); milliseconds %= 1_000
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

        srt_output = ""
        for i, segment in enumerate(final_segments):
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            text = f"[{segment['speaker']}] {segment['text'].strip()}"
            
            srt_output += f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n"

        print("--- Process Complete ---")
        return srt_output

    except Exception as e:
        print(f"ERROR during transcription/diarization process: {e}")
        return f"An error occurred during processing: {e}"


def qa_audio(file_path):
    """
    Sends an audio file directly to the Google Gemini model for QA analysis.
    """
    try:
        api_key_b64 = get_config('API', 'API_Key_B64')
        api_key = base64.b64decode(api_key_b64).decode('utf-8')
        model_name = get_config('API', 'ModelName')
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt_file_path = get_config('Prompts', 'IndividualPromptFile')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        print(f"Uploading audio file to Google: {file_path}")
        audio_file = genai.upload_file(path=file_path)
        print("Audio file uploaded successfully.")

        full_prompt = [prompt_template, audio_file]
        
        print(f"Sending audio and prompt to Gemini model: {model_name}")
        response = model.generate_content(full_prompt)
        print("Received response from Gemini.")
        
        genai.delete_file(audio_file.name)
        print("Cleaned up uploaded file.")
        
        cleaned_json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        
        try:
            report_data = json.loads(cleaned_json_string)
            return report_data
        except json.JSONDecodeError as json_err:
            print(f"ERROR: Failed to parse JSON from model response. Error: {json_err}")
            return {"error": "Failed to parse the AI model's response. The output was not valid JSON."}

    except Exception as e:
        print(f"ERROR during Gemini API call: {e}")
        return {"error": f"An error occurred during AI analysis: {e}"}
