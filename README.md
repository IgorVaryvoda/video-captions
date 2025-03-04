# Video Captions App

A simple application that uses self-hosted Whisper to transcribe videos and showcase them using video.js with captions.

## Features

- Upload videos for transcription
- Automatic caption generation using self-hosted Whisper
- Demo page with video.js player to showcase videos with captions
- VTT caption format support

## Prerequisites

- Python 3.9+ installed
- FFmpeg installed (required for Whisper)
  - On Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - On macOS: `brew install ffmpeg`
  - On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Setup with UV (Recommended)

1. Clone the repository
2. Install UV if not already installed:
   ```
   pip install uv
   ```
3. Create a virtual environment and install dependencies:
   ```
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```
   cp .env.example .env
   # Edit .env if you want to change the Whisper model size
   ```
5. Run the application:
   ```
   flask run
   ```
6. Open your browser and navigate to `http://localhost:5000`

## Alternative Setup with Pip

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Follow steps 4-6 from the UV setup above.

## Whisper Models

The application uses the self-hosted version of Whisper. You can choose different model sizes in the `.env` file:

- `tiny`: Fastest, least accurate
- `base`: Good balance for most uses
- `small`: Better accuracy, still reasonable speed
- `medium`: High accuracy, slower
- `large`: Best accuracy, but requires significant computational resources

## Usage

1. Upload a video file through the web interface
2. Wait for the transcription to complete (time varies based on video length and model size)
3. View the video with generated captions in the demo player
4. Download the generated VTT caption file if needed

## Technologies Used

- Backend: Flask (Python)
- Transcription: Self-hosted Whisper
- Package Management: UV
- Frontend: HTML, CSS, JavaScript
- Video Player: video.js

## License

MIT