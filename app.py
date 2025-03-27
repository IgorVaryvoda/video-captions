import os
import tempfile
import webvtt
import subprocess
import json
import re
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'static/output'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'mp3', 'wav', 'ogg', 'flac', 'm4a'}

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Make sure to bind to 0.0.0.0 when running directly (not through gunicorn)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Add context processor to provide 'now' variable to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

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
        for segment in segments:
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment['text'].strip()}\n\n")

def get_media_type(file_path):
    """
    Check if file is audio or video and if it contains audio streams
    Returns:
    - 'audio': If file is an audio file
    - 'video_with_audio': If file is a video with audio streams
    - 'video_without_audio': If file is a video without audio streams
    """
    try:
        # Get file extension
        file_ext = os.path.splitext(file_path)[1].lower()[1:]

        # Audio file formats
        audio_formats = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}

        # If it's an audio file format, return 'audio'
        if file_ext in audio_formats:
            return 'audio'

        # For video files, check if they have audio streams
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'json',
            file_path
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
        has_audio = len(info.get('streams', [])) > 0

        return 'video_with_audio' if has_audio else 'video_without_audio'
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")
        return 'video_without_audio'  # Default to no audio on error
    except json.JSONDecodeError:
        return 'video_without_audio'  # Default to no audio on error

def extract_audio(video_path):
    """Extract audio from video file using ffmpeg"""
    # Check if video has audio streams
    if not get_media_type(video_path) == 'video_with_audio':
        raise ValueError("This video does not contain any audio streams to transcribe")

    audio_path = os.path.splitext(video_path)[0] + '.mp3'

    try:
        # Use ffmpeg to extract audio to MP3 format (which OpenAI API works well with)
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', video_path,  # Input file
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # MP3 audio codec
            '-ar', '44100',  # 44.1kHz sampling rate
            '-ab', '192k',  # 192kbps bitrate
            '-ac', '2',  # Stereo audio
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

def transcribe_with_openai(audio_path):
    """Transcribe audio file using OpenAI Whisper API"""
    try:
        with open(audio_path, 'rb') as audio_file:
            response = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
            print(response)

        # Create segments from words
        segments = []
        current_segment = {
            'start': response.words[0].start if response.words else 0,
            'end': 0,
            'text': ''
        }

        for word in response.words:
            # Check for natural sentence breaks (period, question mark, exclamation mark)
            is_sentence_end = any(word.word.strip().endswith(p) for p in ['.', '?', '!'])

            # Check for conjunctions that often indicate sentence breaks in German
            is_conjunction = word.word.lower() in ['und', 'aber', 'oder', 'sondern', 'denn', 'weil', 'dass']

            # If there's a gap of more than 1 second, it's a sentence end, or it's a conjunction
            # and we already have some text, start a new segment
            if (word.start - current_segment['end'] > 1.0 or
                is_sentence_end or
                (is_conjunction and current_segment['text'])):
                if current_segment['text']:
                    segments.append(current_segment)
                current_segment = {
                    'start': word.start,
                    'end': word.end,
                    'text': word.word
                }
            else:
                current_segment['end'] = word.end
                current_segment['text'] += ' ' + word.word

        # Add the last segment
        if current_segment['text']:
            segments.append(current_segment)

        return segments

    except Exception as e:
        raise RuntimeError(f"Failed to transcribe audio: {str(e)}")

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
        return jsonify({'error': 'No media file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    try:
        # Save the uploaded file
        file.save(file_path)

        # Get media type (audio, video with audio, or video without audio)
        media_type = get_media_type(file_path)

        if media_type == 'audio':
            # For audio files, copy directly to output
            import shutil
            shutil.copy2(file_path, output_path)
            audio_path = output_path
        elif media_type == 'video_with_audio':
            # For videos with audio, extract the audio for transcription
            audio_path = extract_audio(file_path)
            # Copy the original video to output folder
            import shutil
            shutil.copy2(file_path, output_path)
        else:
            # For videos without audio, create an empty VTT file and copy video
            import shutil
            shutil.copy2(file_path, output_path)
            vtt_output = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(filename)[0] + '.vtt')
            create_empty_vtt(file_path, vtt_output)

            return jsonify({
                'filename': filename,
                'vtt_url': url_for('static', filename=f'output/{os.path.splitext(filename)[0]}.vtt'),
                'warning': 'The uploaded media does not contain any audio to transcribe. An empty caption file has been created.'
            })

        # Transcribe audio with Whisper
        segments = transcribe_with_openai(audio_path)

        # Generate VTT file
        vtt_output = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(filename)[0] + '.vtt')
        create_vtt_file(segments, vtt_output)

        # Clean up temporary files
        if audio_path != output_path:  # Only delete if it's a temporary extracted audio file
            os.remove(audio_path)
        os.remove(file_path)  # Clean up the uploaded file

        # Return success response
        return jsonify({
            'filename': filename,
            'vtt_url': url_for('static', filename=f'output/{os.path.splitext(filename)[0]}.vtt')
        })

    except ValueError as e:
        # If no audio stream is found or other validation error
        if os.path.exists(file_path):
            os.remove(file_path)  # Clean up the uploaded file
        return jsonify({
            'error': str(e),
            'suggestion': 'Please ensure your file has an audio track that can be transcribed.'
        }), 400

    except Exception as e:
        # For any other errors
        if os.path.exists(file_path):
            os.remove(file_path)  # Clean up if possible
        return jsonify({
            'error': f'Error processing file: {str(e)}'
        }), 500

@app.route('/player/<filename>')
def player(filename):
    base_filename = os.path.splitext(filename)[0]
    file_extension = os.path.splitext(filename)[1].lower()[1:]  # Get extension without dot
    vtt_filename = f"{base_filename}.vtt"

    media_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    vtt_path = os.path.join(app.config['OUTPUT_FOLDER'], vtt_filename)

    if not os.path.exists(media_path) or not os.path.exists(vtt_path):
        return "Media or captions not found", 404

    # Check if this is an audio file
    is_audio = file_extension in {'mp3', 'wav', 'ogg', 'flac', 'm4a'}

    media_url = url_for('static', filename=f'output/{filename}')
    vtt_url = url_for('static', filename=f'output/{vtt_filename}')

    return render_template('player.html',
                          media_url=media_url,
                          vtt_url=vtt_url,
                          filename=filename,
                          is_audio=is_audio,
                          file_extension=file_extension)

@app.route('/demo')
def demo():
    # List all processed media files (videos and audio)
    media_files = []
    for filename in os.listdir(app.config['OUTPUT_FOLDER']):
        if allowed_file(filename):
            base_filename = os.path.splitext(filename)[0]
            file_extension = os.path.splitext(filename)[1].lower()[1:]
            vtt_filename = f"{base_filename}.vtt"
            vtt_path = os.path.join(app.config['OUTPUT_FOLDER'], vtt_filename)

            # Only include if .vtt file exists for this media file
            if os.path.exists(vtt_path):
                # Determine if it's audio or video
                is_audio = file_extension in {'mp3', 'wav', 'ogg', 'flac', 'm4a'}

                media_files.append({
                    'filename': filename,
                    'url': url_for('player', filename=filename),
                    'is_audio': is_audio
                })

    # Sort alphabetically
    media_files.sort(key=lambda x: x['filename'])

    return render_template('demo.html', media_files=media_files)