# Google Drive Pictures Compressor

A tool to compress images stored in Google Drive while maintaining reasonable quality.

## Features
- Connects to Google Drive using official API
- Compresses images to a target file size while maintaining quality
- Uploads compressed versions back to the same folder
- Shows progress bar during compression
- Handles errors gracefully

## Setup

1. Make sure you have Python installed on your system
2. Install the required packages:
```
pip install -r requirements.txt
```

3. Set up Google Drive API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `credentials.json` in the same directory as the script

## Usage

Run the script from the command line:
```
python gdrive_compressor.py folder_id [--max-size MAX_SIZE_MB]
```

Arguments:
- `folder_id`: The ID of the Google Drive folder (found in the folder's URL)
- `--max-size`: Maximum size in MB for compressed images (default: 1.0)

Example:
```
python gdrive_compressor.py "1234567890abcdef" --max-size 0.5
```

Note: On first run, the script will open your browser for Google Drive authorization. The access token will be saved locally for future use.
