import os
import io
import tempfile
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from PIL import Image
from tqdm import tqdm
from google.auth.exceptions import RefreshError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']

def get_google_drive_service():
    """Get or create Google Drive API service."""
    creds = None
    
    # Remove existing token to force new authentication
    if os.path.exists('token.json'):
        os.remove('token.json')
        print("Removed existing token to force new authentication")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("Successfully authenticated with Google Drive")
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        print("\nPlease make sure:")
        print("1. You have a valid credentials.json file in the same directory")
        print("2. You've configured the OAuth consent screen in Google Cloud Console")
        print("3. You're using the correct Google account")
        sys.exit(1)

    try:
        service = build('drive', 'v3', credentials=creds)
        # Test the service with a simple API call
        about = service.about().get(fields="user").execute()
        print(f"Authenticated as: {about['user']['emailAddress']}")
        return service
    except Exception as e:
        print(f"Error building Drive service: {str(e)}")
        sys.exit(1)

def compress_image(input_path, max_size_mb=1.0):
    """Compress an image and return bytes IO object."""
    # Open the image
    img = Image.open(input_path)

    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Create a bytes buffer to store the compressed image
    output_buffer = io.BytesIO()

    # Initial quality
    quality = 95
    img.save(output_buffer, format='JPEG', quality=quality, optimize=True)

    # Reduce quality until file size is under max_size_mb
    while output_buffer.tell() > (max_size_mb * 1024 * 1024) and quality > 5:
        output_buffer.seek(0)
        output_buffer.truncate()
        quality -= 5
        img.save(output_buffer, format='JPEG', quality=quality, optimize=True)

    output_buffer.seek(0)
    return output_buffer

def process_drive_folder(service, folder_id, max_size_mb=1.0):
    """Process all images in a Google Drive folder."""
    try:
        # First verify the folder exists and we have access
        try:
            folder = service.files().get(fileId=folder_id).execute()
            print(f"Found folder: {folder.get('name', 'Unnamed folder')}")
        except Exception as e:
            print(f"Error accessing folder: {str(e)}")
            return

        # List all files in the folder
        print("\nScanning folder contents...")
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000
        ).execute()
        
        all_files = results.get('files', [])
        
        if not all_files:
            print("The folder is empty.")
            return
            
        print(f"\nFound {len(all_files)} total files in folder:")
        
        # Filter for image files
        image_files = [f for f in all_files if f['mimeType'].startswith('image/')]
        
        # Print summary of found files
        print(f"Total files: {len(all_files)}")
        print(f"Image files: {len(image_files)}")
        print("\nFile types found:")
        mime_types = {}
        for f in all_files:
            mime_types[f['mimeType']] = mime_types.get(f['mimeType'], 0) + 1
        for mime, count in mime_types.items():
            print(f"- {mime}: {count} files")

        if not image_files:
            print("\nNo image files found to compress.")
            return

        print("\nProcessing images:")
        # Process each image with a progress bar
        for item in tqdm(image_files, desc="Compressing images"):
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # Download file
                    request = service.files().get_media(fileId=item['id'])
                    
                    with io.FileIO(temp_path, 'wb') as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while done is False:
                            _, done = downloader.next_chunk()

                    # Compress the image
                    compressed_buffer = compress_image(temp_path, max_size_mb)

                    # Create file metadata
                    file_metadata = {
                        'name': f"compressed_{item['name']}",
                        'parents': [folder_id]
                    }

                    # Create media
                    media = MediaIoBaseUpload(
                        compressed_buffer,
                        mimetype='image/jpeg',
                        resumable=True
                    )

                    # Upload compressed file
                    upload = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    
                    print(f"\nSuccessfully compressed and uploaded: {item['name']}")

                except Exception as e:
                    print(f"\nError processing {item['name']}: {str(e)}")
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass

            except Exception as e:
                print(f"\nError setting up processing for {item['name']}: {str(e)}")

    except Exception as e:
        print(f"Error processing folder: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compress images in a Google Drive folder")
    parser.add_argument("folder_id", help="Google Drive folder ID")
    parser.add_argument("--max-size", type=float, default=1.0,
                        help="Maximum size in MB for compressed images (default: 1.0)")

    args = parser.parse_args()
    
    print("Authenticating with Google Drive...")
    service = get_google_drive_service()
    print("Processing images...")
    process_drive_folder(service, args.folder_id, args.max_size)
