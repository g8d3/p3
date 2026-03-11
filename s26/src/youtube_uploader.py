#!/usr/bin/env python3
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configuration - Update these paths as needed
CLIENT_SECRET_FILE = "/home/vuos/Downloads/client_secret_206378143571-vpkepe5vu4ddvvkegfqefts15i3rod6r.apps.googleusercontent.com.json"
TOKEN_FILE = "/home/vuos/.youtube/token.pickle"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # FIX: Removed the fixed port to avoid Redirect URI Mismatch
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(open_browser=True)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def initialize_upload(youtube, options):
    tags = options.get('tags', [])
    
    body = {
        'snippet': {
            'title': options['title'],
            'description': options['description'],
            'tags': tags,
            'categoryId': '28'  # Science & Technology
        },
        'status': {
            'privacyStatus': options['privacy'],
            'selfDeclaredMadeForKids': False
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options['file'], chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)

def resumable_upload(request):
    response = None
    error = None
    retry = 0
    max_retries = 5
    
    print(f"📤 Starting upload...")
    
    while response is None:
        try:
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print(f"✅ Video successfully uploaded! ID: {response['id']}")
                    print(f"🔗 URL: https://youtu.be/{response['id']}")
                else:
                    exit(f"❌ The upload failed with an unexpected response: {response}")
            elif status:
                print(f"⏳ Uploaded {int(status.progress() * 100)}%...")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"A retriable HTTP error {e.resp.status} occurred"
            else:
                raise
        except Exception as e:
            error = f"A retriable error occurred: {e}"

        if error:
            print(error)
            retry += 1
            if retry > max_retries:
                exit("❌ Reached maximum retries.")
            print(f"🔄 Retrying {retry}...")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Video file to upload')
    parser.add_argument('--title', help='Video title', required=True)
    parser.add_argument('--description', help='Video description', default='')
    parser.add_argument('--tags', help='Video tags (comma separated)', default='')
    parser.add_argument('--privacy', default='public', choices=['public', 'private', 'unlisted'])
    
    args = parser.parse_args()
    
    # Process tags into a list
    tag_list = [t.strip() for t in args.tags.split(',')] if args.tags else []

    if not os.path.exists(args.file):
        exit(f"❌ Error: File {args.file} not found.")

    try:
        youtube_service = get_authenticated_service()
        initialize_upload(youtube_service, {
            'file': args.file,
            'title': args.title,
            'description': args.description,
            'tags': tag_list,
            'privacy': args.privacy
        })
    except Exception as e:
        print(f"❌ Critical Error: {e}")
