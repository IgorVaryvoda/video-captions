# Using UV with Video Captions App

This document provides detailed instructions for using UV (the Python package installer and environment manager) with the Video Captions App.

## What is UV?

UV is a modern alternative to pip and virtualenv, offering:
- Much faster package installation
- Reliable dependency resolution
- Seamless virtual environment management
- Improved security

Learn more: [UV documentation](https://github.com/astral-sh/uv)

## Setup with UV

### Installing UV

```bash
# Install UV
pip install uv
```

### Creating a Virtual Environment

```bash
# Create a virtual environment in the .venv directory
uv venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### Installing Dependencies

```bash
# Install dependencies using UV
uv pip install -r requirements.txt
```

### Updating Dependencies

```bash
# Update dependencies to their latest compatible versions
uv pip install --upgrade -r requirements.txt
```

## Advantages of UV for This Project

1. **Speed**: UV installs packages (especially Whisper and its dependencies) much faster than pip
2. **Reliability**: Consistent dependency resolution avoids conflicts, particularly important for torch/CUDA compatibility
3. **Reproducibility**: More reliable environment setup across different systems

## Common Commands

```bash
# Install a new package and add it to requirements.txt
uv pip install <package> --update-requirements requirements.txt

# View installed packages
uv pip freeze

# Sync installed packages exactly to requirements.txt
uv pip sync requirements.txt
```

## Troubleshooting

If you encounter issues:

1. Make sure you've activated the virtual environment
2. Try removing the .venv directory and recreating it:
   ```bash
   rm -rf .venv
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```
3. Verify FFmpeg is installed on your system (required for Whisper)