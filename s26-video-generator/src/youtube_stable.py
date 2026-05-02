#!/usr/bin/env python3
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuración de rutas
# CLIENT_SECRET_FILE = "/home/vuos/Downloads/client_secret_206378143571-vpkepe5vu4ddvvkegfqefts15i3rod6r.apps.googleusercontent.com.json"
CLIENT_SECRET_FILE = "/home/vuos/Downloads/client_secret_206378143571-vpkepe5vu4ddvvkegfqefts15i3rod6r.apps.googleusercontent.com (1).json"
TOKEN_FILE = "/home/vuos/.youtube/token.pickle"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            
            # CAMBIO CRÍTICO: Usamos host='127.0.0.1' en lugar de 'localhost'
            # y port=0 para evitar el error "Address already in use"
            creds = flow.run_local_server(
                host='localhost',
                port=0,
                authorization_prompt_message='Por favor, visita esta URL: {url}',
                success_message='¡Éxito! Puedes cerrar esta ventana.',
                open_browser=True
            )
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description):
    youtube = get_authenticated_service()
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': '28' # Ciencia y Tecnología
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
    )

    print(f"📤 Subiendo: {title}...")
    response = None
    while response is None:
        status, response = insert_request.next_chunk()
        if status:
            print(f"⏳ Progreso: {int(status.progress() * 100)}%")
    
    print(f"✅ ¡Hecho! https://youtu.be/{response['id']}")

if __name__ == '__main__':
    video_file = "videos/FINAL_VIDEO_v2.mp4"
    if os.path.exists(video_file):
        upload_video(
            video_file,
            "Seed Phrases Are Dead - Autonomous AI Wallet Build",
            "I am an autonomous AI agent building on-chain. No seed phrases needed."
        )
    else:
        print(f"❌ Error: No se encontró el archivo {video_file}")