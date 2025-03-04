#!/bin/bash

# Video Captions App Setup Script

echo "Setting up Video Captions App..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    pip install uv
fi

# Create virtual environment with UV
echo "Creating virtual environment with UV..."
uv venv

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Virtual environment creation failed."
    exit 1
fi

# Install dependencies with UV
echo "Installing dependencies with UV..."
uv pip install -r requirements.txt

# Check if FFmpeg is installed
echo "Checking for FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: FFmpeg is not installed. It is required for Whisper to work."
    echo "Please install FFmpeg manually:"
    echo "  - Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  - macOS: brew install ffmpeg"
    echo "  - Windows: Download from https://ffmpeg.org/download.html"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads static/output

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env file to configure your environment."
fi

echo ""
echo "Setup completed successfully!"
echo "To run the application:"
echo "  1. Make sure you are in the virtual environment (source .venv/bin/activate)"
echo "  2. Run: flask run"
echo ""
echo "Visit http://localhost:5000 in your browser."