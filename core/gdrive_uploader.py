import os
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.file']
APP_ROOT_FOLDER_NAME = "RoyalRoad Archiver Backups"

def authenticate_gdrive():
    """Authenticates the user with Google Drive API using OAuth 2.0.

    Returns:
        googleapiclient.discovery.Resource: The Google Drive API service object.
    """
    creds = None
    print("Authenticating...")

    # Check for token.json
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as token:
                creds_json = json.load(token)
            # Manually construct credentials from stored JSON
            creds = build('drive', 'v3').files()._http.credentials.from_authorized_user_info(creds_json, SCOPES)

        except Exception as e:
            print(f"Error loading token.json: {e}. Will try to re-authenticate.")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                creds = None # Force re-authentication
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found in the project root.")
                print("Please download your OAuth 2.0 credentials from Google Cloud Console")
                print("and place it as 'credentials.json' in the root directory.")
                raise FileNotFoundError("credentials.json not found.")

            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            # We need to store the token in a way that from_authorized_user_info can read
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            json.dump(token_data, token)
        print("Authentication successful and token saved.")

    try:
        service = build('drive', 'v3', credentials=creds)
        print("Google Drive API service created successfully.")
        return service
    except Exception as e:
        print(f"Failed to build Google Drive service: {e}")
        raise

def get_or_create_folder_id(service, folder_name, parent_folder_id=None):
    """Searches for a folder by name within a parent folder (or root) and creates it if not found.

    Args:
        service: The authenticated Google Drive API service object.
        folder_name (str): The name of the folder to find or create.
        parent_folder_id (str, optional): The ID of the parent folder. Defaults to None (root).

    Returns:
        str: The ID of the found or created folder.
    """
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    print(f"Searching for folder: '{folder_name}'" + (f" in parent ID: {parent_folder_id}" if parent_folder_id else ""))
    try:
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])

        if folders:
            folder_id = folders[0].get('id')
            print(f"Folder '{folder_name}' found with ID: {folder_id}")
            return folder_id
        else:
            print(f"Folder '{folder_name}' not found. Creating it...")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Folder '{folder_name}' created with ID: {folder_id}")
            return folder_id
    except HttpError as error:
        print(f"An error occurred while searching/creating folder '{folder_name}': {error}")
        raise

def upload_file_to_gdrive(service, local_filepath, gdrive_folder_id):
    """Uploads a local file to the specified Google Drive folder.

    Args:
        service: The authenticated Google Drive API service object.
        local_filepath (str): The path to the local file to upload.
        gdrive_folder_id (str): The ID of the Google Drive folder to upload the file to.

    Returns:
        str: The ID of the uploaded file, or None if upload failed.
    """
    if not os.path.exists(local_filepath):
        print(f"Error: Local file '{local_filepath}' not found.")
        return None

    filename = os.path.basename(local_filepath)
    print(f"Processing file '{filename}' for Google Drive folder ID: {gdrive_folder_id}...")

    media = MediaFileUpload(local_filepath, resumable=True)
    
    try:
        # Search for existing file
        query = f"name='{filename}' and '{gdrive_folder_id}' in parents and trashed=false"
        print(f"Searching for existing file with query: {query}")
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        existing_files = response.get('files', [])

        if existing_files:
            existing_file = existing_files[0]
            existing_file_id = existing_file.get('id')
            print(f"Found existing file '{existing_file.get('name')}' with ID: {existing_file_id}. Updating it.")
            
            # Update existing file
            updated_file = service.files().update(fileId=existing_file_id,
                                                 media_body=media,
                                                 fields='id, name').execute()
            print(f"File '{updated_file.get('name')}' updated successfully with ID: {updated_file.get('id')}")
            return updated_file.get('id')
        else:
            print(f"No existing file found with name '{filename}' in folder '{gdrive_folder_id}'. Creating new file.")
            # Create new file
            file_metadata = {
                'name': filename,
                'parents': [gdrive_folder_id]
            }
            new_file = service.files().create(body=file_metadata,
                                          media_body=media,
                                          fields='id, name').execute()
            print(f"File '{new_file.get('name')}' created successfully with ID: {new_file.get('id')}")
            return new_file.get('id')

    except HttpError as error:
        print(f"An API error occurred during file operation for '{filename}': {error}")
        if error.resp.status == 401:
             print("Authentication error: Please ensure your token is valid or re-authenticate.")
        elif error.resp.status == 403:
            print("Permission error: Ensure the authenticated user has permission for this operation on the target folder/file.")
        elif error.resp.status == 404:
            # This could be for the folder in create, or file in update.
            print(f"Error: Google Drive folder with ID '{gdrive_folder_id}' not found, or file not found for update.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during file operation for '{filename}': {e}")
        return None

def upload_story_files(service, story_slug):
    """Orchestrates the upload of a story's files (EPUBs and metadata) to Google Drive.

    Args:
        service: The authenticated Google Drive API service object.
        story_slug (str): The unique slug for the story.
    """
    print(f"Starting upload process for story: {story_slug}")
    try:
        # 1. Get or create the main application folder
        app_root_folder_id = get_or_create_folder_id(service, APP_ROOT_FOLDER_NAME)
        if not app_root_folder_id:
            print(f"Could not get or create the root application folder '{APP_ROOT_FOLDER_NAME}'. Aborting upload for {story_slug}.")
            return

        # 2. Get or create the specific story folder inside the application root folder
        story_gdrive_folder_id = get_or_create_folder_id(service, story_slug, parent_folder_id=app_root_folder_id)
        if not story_gdrive_folder_id:
            print(f"Could not get or create the story folder '{story_slug}'. Aborting upload.")
            return

        # 3. Upload EPUBs
        epubs_dir = os.path.join("epubs", story_slug)
        if os.path.exists(epubs_dir) and os.path.isdir(epubs_dir):
            print(f"Searching for EPUB files in: {epubs_dir}")
            for filename in os.listdir(epubs_dir):
                if filename.endswith(".epub"):
                    local_epub_path = os.path.join(epubs_dir, filename)
                    print(f"Found EPUB: {local_epub_path}. Uploading...")
                    upload_file_to_gdrive(service, local_epub_path, story_gdrive_folder_id)
        else:
            print(f"No EPUBs directory found for story slug '{story_slug}' at '{epubs_dir}'.")

        # 4. Upload metadata file
        metadata_file = os.path.join("metadata_store", story_slug, "download_status.json")
        if os.path.exists(metadata_file):
            print(f"Found metadata file: {metadata_file}. Uploading...")
            upload_file_to_gdrive(service, metadata_file, story_gdrive_folder_id)
        else:
            print(f"No download_status.json found for story slug '{story_slug}' at '{metadata_file}'.")
        
        print(f"Finished upload process for story: {story_slug}")

    except HttpError as error:
        print(f"An HTTP error occurred during the upload process for '{story_slug}': {error}")
    except Exception as e:
        print(f"An unexpected error occurred during the upload process for '{story_slug}': {e}")


if __name__ == '__main__':
    # This is a basic test sequence.
    # In a real application, you would call these functions from other parts of your code.
    
    # Create dummy credentials.json for testing if it doesn't exist
    # IMPORTANT: Replace this with your actual credentials.json from Google Cloud Console
    if not os.path.exists('credentials.json'):
        print("Creating a placeholder credentials.json for demonstration.")
        print("Please replace 'credentials.json' with your actual credentials from Google Cloud Console.")
        placeholder_credentials = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID",
                "project_id": "YOUR_PROJECT_ID",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }
        with open('credentials.json', 'w') as f:
            json.dump(placeholder_credentials, f)

    try:
        drive_service = authenticate_gdrive()
        if drive_service:
            # --- Test get_or_create_folder_id and upload_file_to_gdrive (original test) ---
            # test_main_folder_name = "MyNovelWriterEpubs_OriginalTest" 
            # test_book_subfolder_name = "Test Book Original" 
            # main_folder_id_orig = get_or_create_folder_id(drive_service, test_main_folder_name)
            # if main_folder_id_orig:
            #     book_folder_id_orig = get_or_create_folder_id(drive_service, test_book_subfolder_name, main_folder_id_orig)
            #     if book_folder_id_orig:
            #         dummy_file_name = "test_upload_original.txt"
            #         with open(dummy_file_name, "w") as f: f.write("Original test file.")
            #         upload_file_to_gdrive(drive_service, dummy_file_name, book_folder_id_orig)
            #         if os.path.exists(dummy_file_name): os.remove(dummy_file_name)
            # else:
            #     print(f"Could not create/get '{test_main_folder_name}' for original test.")

            # --- Test upload_story_files ---
            print("\n--- Testing upload_story_files ---")
            test_story_slug = "my-test-story-slug"
            
            # Create dummy local files for testing upload_story_files
            # Dummy EPUB
            os.makedirs(os.path.join("epubs", test_story_slug), exist_ok=True)
            dummy_epub_path = os.path.join("epubs", test_story_slug, "MyTestStory.epub")
            with open(dummy_epub_path, "w") as f:
                f.write("This is a dummy EPUB file content.")
            
            # Dummy metadata
            os.makedirs(os.path.join("metadata_store", test_story_slug), exist_ok=True)
            dummy_metadata_path = os.path.join("metadata_store", test_story_slug, "download_status.json")
            with open(dummy_metadata_path, "w") as f:
                json.dump({"title": "My Test Story", "status": "completed"}, f)

            upload_story_files(drive_service, test_story_slug)
            
            # Clean up dummy files and folders
            print(f"\n--- Cleaning up test files for {test_story_slug} ---")
            if os.path.exists(dummy_epub_path):
                os.remove(dummy_epub_path)
            if os.path.exists(os.path.join("epubs", test_story_slug)):
                os.rmdir(os.path.join("epubs", test_story_slug)) # rmdir only if empty
            if os.path.exists("epubs"): # clean up "epubs" if it's empty
                 if not os.listdir("epubs"):
                    os.rmdir("epubs")

            if os.path.exists(dummy_metadata_path):
                os.remove(dummy_metadata_path)
            if os.path.exists(os.path.join("metadata_store", test_story_slug)):
                os.rmdir(os.path.join("metadata_store", test_story_slug)) # rmdir only if empty
            if os.path.exists("metadata_store"): # clean up "metadata_store" if it's empty
                if not os.listdir("metadata_store"): # Check if directory is empty
                    try:
                        os.rmdir("metadata_store")
                    except OSError as e:
                        print(f"Error removing metadata_store (it might not be empty or permissions issue): {e}")

            print(f"--- Finished testing upload_story_files for {test_story_slug} ---")

            # --- Test Update/Replace Logic ---
            print("\n--- Testing Update/Replace Logic ---")
            update_test_story_slug = "test-update-logic-story"
            update_test_epub_filename = "test_update_story.epub"
            local_update_test_epub_dir = os.path.join("epubs", update_test_story_slug)
            local_update_test_epub_path = os.path.join(local_update_test_epub_dir, update_test_epub_filename)

            os.makedirs(local_update_test_epub_dir, exist_ok=True)

            print(f"\n[Update Test] Step 1: Initial Upload for '{update_test_story_slug}'")
            print(f"Creating dummy file: {local_update_test_epub_path} with initial content.")
            with open(local_update_test_epub_path, "w") as f:
                f.write("This is the first version of the test EPUB.")
            
            print("Calling upload_story_files. OBSERVE: Log messages should indicate a NEW file is being CREATED.")
            upload_story_files(drive_service, update_test_story_slug)

            print(f"\n[Update Test] Step 2: Modifying Local File for '{update_test_story_slug}'")
            print(f"Modifying content of: {local_update_test_epub_path}")
            with open(local_update_test_epub_path, "w") as f:
                f.write("This is the **UPDATED** version of the test EPUB.")

            print("Calling upload_story_files again. OBSERVE: Log messages should indicate an EXISTING file is being UPDATED.")
            upload_story_files(drive_service, update_test_story_slug)

            print(f"\n[Update Test] Step 3: Verification (Manual)")
            print(f"Please manually check Google Drive in folder '{APP_ROOT_FOLDER_NAME}/{update_test_story_slug}'")
            print(f"Verify that '{update_test_epub_filename}' exists and its content is the **UPDATED** version.")
            # input("Press Enter to continue after manual verification...") # Optional: pause for manual check

            print(f"\n--- Cleaning up test files for {update_test_story_slug} ---")
            if os.path.exists(local_update_test_epub_path):
                os.remove(local_update_test_epub_path)
            if os.path.exists(local_update_test_epub_dir):
                try:
                    os.rmdir(local_update_test_epub_dir) # rmdir only if empty
                except OSError as e:
                     print(f"Note: Could not remove directory {local_update_test_epub_dir}. It might not be empty if other files were created (e.g. metadata). This is okay for this test's cleanup.")
            
            # Attempt to clean up the parent 'epubs' directory if it's empty
            if os.path.exists("epubs") and not os.listdir("epubs"):
                try:
                    os.rmdir("epubs")
                except OSError as e:
                    print(f"Error removing epubs (it might not be empty or permissions issue): {e}")
            print(f"--- Finished testing Update/Replace Logic for {update_test_story_slug} ---")

    except FileNotFoundError as e:
        print(f"Setup error: {e}. Ensure credentials.json is in the root or a placeholder is created.")
    except Exception as e:
        print(f"An unexpected error occurred in the main test script: {e}")
    finally:
        # Clean up placeholder credentials.json if it was created by this script
        # and if it's the dummy one.
        if os.path.exists('credentials.json'):
            try:
                with open('credentials.json', 'r') as f:
                    creds_data = json.load(f)
                if creds_data.get("installed", {}).get("client_id") == "YOUR_CLIENT_ID":
                    # print("Note: Placeholder credentials.json ('YOUR_CLIENT_ID') was used for testing.")
                    # print("Consider removing 'credentials.json' and 'token.json' if you used placeholder credentials and want to re-authenticate with real credentials next time.")
                    pass # Keep placeholder for now for easier re-testing
            except json.JSONDecodeError:
                print("Warning: credentials.json is malformed.")
            except Exception as e:
                print(f"Error during cleanup check of credentials.json: {e}")
        
        # For testing, it's often useful to remove token.json to force re-auth on next run,
        # especially if testing with placeholder credentials.
        # if os.path.exists('token.json'):
        #     print("Consider removing 'token.json' to force re-authentication on the next run, especially after testing.")
        #     # os.remove('token.json') # Uncomment to auto-remove token for fresh auth next run
        print("Test script finished.")
        pass
