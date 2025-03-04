import os
import tempfile
import whisper
import torch
import webvtt
import subprocess
import json
import re
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'static/output'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Add context processor to provide 'now' variable to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Load Whisper model (lazy loading to save memory)
model = None

def get_model():
    global model
    if model is None:
        model_name = os.getenv('WHISPER_MODEL', 'base')
        print(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name)
    return model

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def format_timestamp(seconds):
    """Convert seconds to VTT timestamp format"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def create_vtt_file(segments, output_path):
    """Create VTT file from whisper segments"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for i, segment in enumerate(segments):
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment['text'].strip()}\n\n")

def check_audio_stream(video_path):
    """Check if video file contains audio streams"""
    try:
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        # Parse the JSON output
        info = json.loads(result.stdout)

        # Check if there are any audio streams
        return len(info.get('streams', [])) > 0
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")
        return False
    except json.JSONDecodeError:
        return False

def extract_audio(video_path):
    """Extract audio from video file using ffmpeg"""
    # Check if video has audio streams
    if not check_audio_stream(video_path):
        raise ValueError("This video does not contain any audio streams to transcribe")

    audio_path = os.path.splitext(video_path)[0] + '.wav'

    try:
        # Use ffmpeg to extract audio to WAV format (which Whisper handles well)
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', video_path,  # Input file
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian audio codec
            '-ar', '16000',  # 16kHz sampling rate (which Whisper expects)
            '-ac', '1',  # Mono audio
            audio_path  # Output file
        ]

        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")

        # Check if the error is about no audio streams
        error_msg = e.stderr
        if "does not contain any stream" in error_msg or "Output file does not contain any stream" in error_msg:
            raise ValueError("This video does not contain any audio streams to transcribe")

        raise RuntimeError(f"Failed to extract audio: {e.stderr}")

def create_empty_vtt(video_path, output_path):
    """Create an empty VTT file for videos without audio"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        f.write("00:00:00.000 --> 00:00:05.000\n")
        f.write("This video appears to have no audio content to transcribe.\n\n")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'}), 400

    # Save uploaded file
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Get base filename without extension
    base_filename = os.path.splitext(filename)[0]

    try:
        # Check if video has audio
        has_audio = check_audio_stream(file_path)

        # Save processed video to output directory
        output_video_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        vtt_filename = f"{base_filename}.vtt"
        vtt_path = os.path.join(app.config['OUTPUT_FOLDER'], vtt_filename)

        # If the processed video doesn't exist in the output folder, copy it there
        if not os.path.exists(output_video_path):
            import shutil
            shutil.copy2(file_path, output_video_path)

        if has_audio:
            # Extract audio from video
            audio_path = extract_audio(file_path)

            # Transcribe with Whisper
            model = get_model()
            result = model.transcribe(audio_path)

            # Create VTT file
            create_vtt_file(result['segments'], vtt_path)
        else:
            # Create an empty VTT file with a message
            create_empty_vtt(file_path, vtt_path)
            return jsonify({
                'success': True,
                'warning': 'No audio detected in this video. Created an empty caption file.',
                'video_url': url_for('static', filename=f'output/{filename}'),
                'vtt_url': url_for('static', filename=f'output/{vtt_filename}'),
                'filename': filename
            })

        return jsonify({
            'success': True,
            'video_url': url_for('static', filename=f'output/{filename}'),
            'vtt_url': url_for('static', filename=f'output/{vtt_filename}'),
            'filename': filename
        })

    except ValueError as e:
        # User-friendly error for no audio
        return jsonify({
            'error': str(e),
            'suggestion': 'Please upload a video that contains audio to transcribe.',
            'video_url': url_for('static', filename=f'output/{filename}'),
            'filename': filename
        }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/player/<filename>')
def player(filename):
    base_filename = os.path.splitext(filename)[0]
    vtt_filename = f"{base_filename}.vtt"

    video_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    vtt_path = os.path.join(app.config['OUTPUT_FOLDER'], vtt_filename)

    if not os.path.exists(video_path) or not os.path.exists(vtt_path):
        return "Video or captions not found", 404

    video_url = url_for('static', filename=f'output/{filename}')
    vtt_url = url_for('static', filename=f'output/{vtt_filename}')

    return render_template('player.html',
                          video_url=video_url,
                          vtt_url=vtt_url,
                          filename=filename)

@app.route('/demo')
def demo():
    # List all processed videos
    videos = []
    for filename in os.listdir(app.config['OUTPUT_FOLDER']):
        if allowed_file(filename):
            base_filename = os.path.splitext(filename)[0]
            vtt_filename = f"{base_filename}.vtt"
            vtt_path = os.path.join(app.config['OUTPUT_FOLDER'], vtt_filename)

            if os.path.exists(vtt_path):
                videos.append({
                    'filename': filename,
                    'url': url_for('player', filename=filename)
                })

    return render_template('demo.html', videos=videos)

if __name__ == '__main__':
    app.run(debug=True)