---
name: google-drive-document-retrieval
description: Retrieve documents from Google Drive using service account credentials
category: mcp
---
# skill: google-drive-document-retrieval

## Purpose
Retrieve documents from Google Drive using service account credentials. Useful when you need to access specific documents stored in Google Drive that are relevant to the current task (e.g., instructions, specifications, configuration files).

## When to Use
- You know a document exists in Google Drive but don't have the local path
- You have service account credentials configured for Google Drive access
- You need to retrieve instructions, specifications, or other reference materials from Google Drive
- Local and GitHub searches have failed to locate the needed document

## Prerequisites
1. Google service account credentials JSON file available (typically in ~/.hermes/ or similar location)
2. The service account must have access to the target Google Drive folder or file
3. Required Python packages: google-api-python-client, google-auth-httplib2, google-auth-oauthlib

## Process
1. **Locate credentials**: Find the service account JSON file (common locations: ~/.hermes/*-iam*.json, ~/.config/gcloud/, etc.)
2. **Authenticate**: Use the service account credentials to build a Google Drive service client
3. **Search**: Locate the target file using:
   - Known file name and/or folder ID
   - Search queries (name contains, specific folder, etc.)
   - Recursive folder traversal if folder structure is unknown
4. **Download**: Retrieve the file content using the Drive API
5. **Process**: Extract and return the content based on file type (text/markdown, etc.)

## Step-by-Step Instructions

### 1. Locate Service Account Credentials
```bash
# Common locations to check
find ~/.hermes -name "*service*" -o -name "*credential*" 2>/dev/null | grep -i json
find ~/.config -name "*service*" 2>/dev/null | grep -i json
```

### 2. Python Retrieval Script Template
```python
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

def retrieve_google_drive_document(service_account_file, file_id=None, file_name=None, folder_id=None):
    """
    Retrieve a document from Google Drive using service account credentials.
    
    Args:
        service_account_file: Path to the service account JSON file
        file_id: Specific file ID (if known)
        file_name: Name of the file to search for
        folder_id: Folder ID to search within (optional)
    
    Returns:
        File content as string, or None if not found
    """
    # Define scopes
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    
    # Build service
    service = build('drive', 'v3', credentials=credentials)
    
    # Build search query
    query_parts = ["trashed=false"]
    
    if file_id:
        # Direct access by ID
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            return fh.read().decode('utf-8')
        except Exception as e:
            print(f"Error accessing file by ID: {e}")
            return None
    
    if file_name:
        query_parts.append(f"name='{file_name}'")
    
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    
    query = " and ".join(query_parts)
    
    # Search for files
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print(f"No files found matching criteria")
        return None
    
    # If multiple files, take the first one (or implement more sophisticated selection)
    target_file = items[0]
    print(f"Found file: {target_file['name']} (ID: {target_file['id']})")
    
    # Download the file
    request = service.files().get_media(fileId=target_file['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    # Get content
    fh.seek(0)
    content = fh.read().decode('utf-8')
    return content

# Example usage:
# content = retrieve_google_drive_document(
#     service_account_file='/root/.hermes/hermesagent-491619-8ac02d8e3571.json',
#     file_name='ELISE_HERMES_INSTRUCTIONS.md',
#     folder_id='1xjVefnsNJOce7ae0gkXG0bYLRS-J20IX'  # Optional: specify folder to search
# )
```

### 3. Alternative: Direct API Call (when you know the exact file ID)
If you know the exact file ID and have the service account credentials:

```bash
# This is handled internally by the Python script above
# The key steps are:
# 1. Authenticate with service account
# 2. Call files.get_media with the file ID
# 3. Download the media chunk by chunk
# 4. Decode and return the content
```

### 4. Recursive Folder Search (when folder structure is unknown)
```python
def search_recursive(service, folder_id, target_filename, depth=0, max_depth=5):
    """Recursively search folders for a target file."""
    if depth > max_depth:
        return None
    
    indent = "  " * depth
    try:
        # Search in current folder
        query = f"'{folder_id}' in parents and trashed=false and name='{target_filename}'"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if items:
            return items[0]  # Return first match
        
        # Search subfolders
        subfolders_query = f"'{folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
        subresults = service.files().list(q=subfolders_query, fields="files(id, name)").execute()
        subfolders = subresults.get('files', [])
        
        for subfolder in subfolders:
            print(f"{indent}Searching subfolder: {subfolder['name']}")
            result = search_recursive(service, subfolder['id'], target_filename, depth + 1, max_depth)
            if result:
                return result
                
    except Exception as e:
        print(f"{indent}Error searching folder: {e}")
    
    return None
```

## Verification Steps
After retrieving a document:
1. Confirm the content matches expectations (check file name, structure, etc.)
2. For markdown/text files, verify readability
3. Check that you got the complete content (not truncated)
4. If searching by name, consider if there might be multiple matches and whether you need to verify you got the right one

## Common Pitfalls and Solutions
- **Authentication errors**: Verify the service account file is valid and not expired
- **Permission denied**: Ensure the service account has access to the file/folder (may need to share the file with the service account email)
- **File not found**: Double-check the file name and folder ID; consider recursive search
- **Download incomplete**: Ensure you're reading the full content after downloading (seek(0) before read())
- **Encoding issues**: Most text files are UTF-8, but verify if you get strange characters
- **API quota errors**: Google Drive API has limits; cache results when possible for repeated access

## Environment Notes
- Works best when service account credentials are available in ~/.hermes/ or similar secure location
- The retrieved content can be saved to a temporary file if needed for further processing
- For frequent access to the same document, consider caching the content or file ID
- Remember that service accounts act as themselves, not as any human user, so sharing is required

## Related Knowledge
- This skill complements the native-mcp skill for when you have MCP servers configured
- Use this when you need to access arbitrary documents not exposed through MCP
- The approach is similar to accessing other Google APIs (Sheets, Docs) with service accounts
- For public Google Drive files, you might not need authentication, but private files require this approach

## Example from Recent Use
Successfully retrieved ELISE_HERMES_INSTRUCTIONS.md from:
- Service account: ~/.hermes/hermesagent-491619-8ac02d8e3571.json
- File name: ELISE_HERMES_INSTRUCTIONS.md
- Located in folder: 280326 (within parent folder 1xjVefnsNJOce7ae0gkXG0bYLRS-J20IX)
- Used recursive search to navigate folder structure when direct folder search didn't immediately yield results
- Key learning: Fixed MediaIoBaseDownload usage - use `status, done = downloader.next_chunk()` not `status, downloader = downloader.next_chunk()`