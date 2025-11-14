import streamlit as st
import tempfile
import os
from docx import Document
import io
import time
import subprocess
import pickle
import json # New import

# Import Google Cloud Libraries
from google.cloud import speech
from google.cloud import storage
import google.generativeai as genai

# Import Google Auth & Drive Libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- NEW: Import Basecamp & formatting tools ---
import requests
from requests_oauthlib import OAuth2Session
from docx.shared import Pt, Inches

# -----------------------------------------------------
# 1. CONSTANTS & CONFIGURATION
#    (We now load these from st.secrets)
# -----------------------------------------------------

# --- Google Config ---
GCS_BUCKET_NAME = st.secrets.get("GCS_BUCKET_NAME", "default-bucket-name")
DRIVE_FOLDER_ID = st.secrets.get("DRIVE_FOLDER_ID", "default-folder-id")
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- Basecamp Config ---
BASECAMP_ACCOUNT_ID = st.secrets["BASECAMP_ACCOUNT_ID"]
BASECAMP_CLIENT_ID = st.secrets["BASECAMP_CLIENT_ID"]
BASECAMP_CLIENT_SECRET = st.secrets["BASECAMP_CLIENT_SECRET"]
YOUR_PERMANENT_REFRESH_TOKEN = st.secrets["BASECAMP_REFRESH_TOKEN"]

# Basecamp API URLs
BASECAMP_TOKEN_URL = "https://launchpad.37signals.com/authorization/token"
BASECAMP_API_BASE = f"https://3.basecampapi.com/{BASECAMP_ACCOUNT_ID}"
BASECAMP_USER_AGENT = {"User-Agent": "AI Meeting Notes App (your-email@example.com)"}


# -----------------------------------------------------
# 2. API CLIENTS SETUP (NOW USING ST.SECRETS)
# -----------------------------------------------------
try:
    # Get the service account JSON from secrets
    sa_creds_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
    sa_creds = service_account.Credentials.from_service_account_info(sa_creds_info)
    
    storage_client = storage.Client(credentials=sa_creds)
    speech_client = speech.SpeechClient(credentials=sa_creds)
except Exception as e:
    st.error(f"FATAL ERROR: Could not load Google Cloud credentials from secrets. Error: {e}")
    st.stop()

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Error initializing Gemini. Is your GOOGLE_API_KEY correct? Error: {e}")
    st.stop()

# --- NEW Google Drive Service (using Refresh Token) ---
@st.cache_resource
def get_drive_service():
    """
    This function uses a permanent refresh token from st.secrets to get
    Google Drive credentials.
    """
    try:
        # Get client secret info and refresh token from secrets
        client_config_str = st.secrets["GDRIVE_CLIENT_SECRET_JSON"]
        client_config = json.loads(client_config_str)
        refresh_token = st.secrets["GDRIVE_REFRESH_TOKEN"]

        # Create credentials object
        creds = Credentials.from_authorized_user_info(
            {
                "client_id": client_config["web"]["client_id"],
                "client_secret": client_config["web"]["client_secret"],
                "refresh_token": refresh_token,
                "token_uri": client_config["web"]["token_uri"],
            }
        )
        
        # Refresh the credentials if they are expired
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                st.error("Error with Google Drive credentials. Please re-generate refresh token.")
                st.stop()

        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"FATAL ERROR: Could not load Google Drive credentials. Error: {e}")
        st.stop()

drive_service = get_drive_service()


# --- NEW: Basecamp Service (Refresh Token Method) ---
@st.cache_resource
def get_basecamp_session():
    """
    This function uses a permanent refresh token from st.secrets to get a new
    access token every time the app starts.
    """
    # We use a temporary file path for the pickle in the cloud
    token_pickle_path = "/tmp/basecamp_token.pickle"
    token = None
    
    if os.path.exists(token_pickle_path):
        with open(token_pickle_path, "rb") as f:
            token = pickle.load(f)

    if token and time.time() < token.get("expires_at", 0):
        session = OAuth2Session(BASECAMP_CLIENT_ID, token=token)
        session.headers.update(BASECAMP_USER_AGENT)
        return session

    st.info("Refreshing Basecamp authorization...")
    try:
        oauth = OAuth2Session(BASECAMP_CLIENT_ID)
        
        new_token = oauth.refresh_token(
            BASECAMP_TOKEN_URL, 
            client_id=BASECAMP_CLIENT_ID,
            client_secret=BASECAMP_CLIENT_SECRET,
            refresh_token=YOUR_PERMANENT_REFRESH_TOKEN,
            type="refresh"
        )
        
        with open(token_pickle_path, "wb") as f:
            pickle.dump(new_token, f)
            
        session = OAuth2Session(BASECAMP_CLIENT_ID, token=new_token)
        session.headers.update(BASECAMP_USER_AGENT)
        st.success("Basecamp is connected.")
        return session
        
    except Exception as e:
        st.error(f"Error refreshing Basecamp token: {e}")
        st.stop()

# -----------------------------------------------------
# 3. HELPER FUNCTIONS (Unchanged)
# -----------------------------------------------------

def upload_to_gcs(file_path, destination_blob_name):
    try: