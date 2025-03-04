# Video Captions App

A simple application that uses OpenAI Whisper API to transcribe videos and showcase them using video.js with captions.

## Features

- Upload videos for transcription
- Automatic caption generation using OpenAI Whisper API
- Demo page with video.js player to showcase videos with captions
- VTT caption format support

## Prerequisites

- Python 3.9+ installed
- FFmpeg installed (required for audio extraction)
  - On Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - On macOS: `brew install ffmpeg`
  - On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Local Setup with UV (Recommended)

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
   # Edit .env to add your OpenAI API key
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

## Deployment to Fly.io

This app is configured for easy deployment to Fly.io using their free tier:

1. Install the Fly CLI:
   ```
   curl -L https://fly.io/install.sh | sh
   ```

2. Log in to Fly.io:
   ```
   ~/.fly/bin/flyctl auth login
   ```

3. Launch your application (from the project directory):
   ```
   ~/.fly/bin/flyctl launch
   ```

4. Create a volume for persistent storage:
   ```
   ~/.fly/bin/flyctl volumes create video_data --size 1
   ```

5. Set your OpenAI API key as a secret:
   ```
   ~/.fly/bin/flyctl secrets set OPENAI_API_KEY=your_api_key_here
   ```

6. Deploy your application:
   ```
   ~/.fly/bin/flyctl deploy
   ```

Your application will be available at `https://video-captions.fly.dev` (or the URL assigned during the launch process).

## Usage

1. Upload a video file through the web interface
2. Wait for the transcription to complete (typically a few seconds)
3. View the video with generated captions in the demo player
4. Download the generated VTT caption file if needed

## Technologies Used

- Backend: Flask (Python)
- Transcription: OpenAI Whisper API
- Package Management: UV
- Frontend: HTML, CSS, JavaScript
- Video Player: video.js
- Deployment: Fly.io

## License

MIT