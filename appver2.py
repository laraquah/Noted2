# 2. HELPER: GET USER IDENTITY
# -----------------------------------------------------
def fetch_basecamp_name(token_dict):
    """Calls Basecamp Identity API to get the user's real name."""
try:
identity_url = "https://launchpad.37signals.com/authorization.json"
headers = {
@@ -99,8 +98,6 @@ def fetch_basecamp_name(token_dict):
st.session_state.basecamp_token = None
if 'user_real_name' not in st.session_state:
st.session_state.user_real_name = ""

# --- METADATA STATES ---
if 'detected_date' not in st.session_state:
st.session_state.detected_date = None
if 'detected_time' not in st.session_state:
@@ -149,7 +146,7 @@ def fetch_basecamp_name(token_dict):
st.error(f"Auto-login failed: {e}")

# -----------------------------------------------------
# 4. SIDEBAR UI (ENFORCED WORKFLOW)
# 4. SIDEBAR UI
# -----------------------------------------------------
with st.sidebar:
st.title("🔐 Login")
@@ -162,19 +159,15 @@ def fetch_basecamp_name(token_dict):
if st.button("Logout Basecamp"):
st.session_state.basecamp_token = None
st.session_state.user_real_name = ""
            st.session_state.gdrive_creds = None
            st.session_state.gdrive_creds_json = None
st.rerun()
else:
bc_oauth = OAuth2Session(BASECAMP_CLIENT_ID, redirect_uri=BASECAMP_REDIRECT_URI)
bc_auth_url, _ = bc_oauth.authorization_url(BASECAMP_AUTH_URL, type="web_server")

if AUTO_LOGIN_MODE:
            # Native Streamlit Link Button
st.link_button("Login to Basecamp", bc_auth_url, type="primary")
st.caption("Opens in a new tab. Close it after logging in.")
else:
            st.warning("Auto-login not configured in Secrets.")
st.markdown(f"👉 [**Authorize Basecamp**]({bc_auth_url})")
bc_code = st.text_input("Paste Basecamp Code:", key="bc_code")
if bc_code:
@@ -231,15 +224,15 @@ def fetch_basecamp_name(token_dict):
st.error(f"Config Error: {e}")

# -----------------------------------------------------
# 5. SECURITY LOCK 🔒
# 5. SECURITY LOCK
# -----------------------------------------------------
if not (st.session_state.basecamp_token and st.session_state.gdrive_creds):
st.title("🔒 Access Restricted")
    st.warning("Please log in to **Basecamp** and **Google Drive** in the sidebar to unlock the AI Meeting Manager.")
    st.warning("Please log in to **Basecamp** and **Google Drive** in the sidebar.")
st.stop() 

# =====================================================
#     MAIN APP LOGIC (Unlocked)
#     MAIN APP LOGIC
# =====================================================

# --- API CLIENTS ---
@@ -255,11 +248,55 @@ def fetch_basecamp_name(token_dict):
st.stop()

# -----------------------------------------------------
# 6. HELPER FUNCTIONS
# 6. HELPER FUNCTIONS (UPDATED FOR FORMATTING)
# -----------------------------------------------------

def _add_rich_text(paragraph, text):
    """Parses markdown-style **bold** text and applies Word formatting."""
    # Regex to split by **text**
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            # Remove asterisks and make bold
            clean_text = part[2:-2]
            run = paragraph.add_run(clean_text)
            run.bold = True
        else:
            # Regular text
            paragraph.add_run(part)

def add_formatted_text(cell, text):
    """Enhanced parser to handle bullets and bold text correctly in Word table cells."""
    cell.text = ""
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2) # Slight spacing for readability
        
        if line.startswith('##'):
            # Heading style within cell
            clean_title = line.lstrip('#').strip()
            run = p.add_run(clean_title)
            run.underline = True
            run.bold = True
            p.paragraph_format.space_before = Pt(8)
        elif line.startswith('*') or line.startswith('-'):
            # Bullet point with rich text support
            clean_text = line.lstrip('*- ').strip()
            p.style = 'List Bullet' # Use Word's native bullet style if available
            # If style fails, manual bullet:
            if not p.style: p.text = "• "
            _add_rich_text(p, clean_text)
        else:
            # Normal paragraph with rich text support
            _add_rich_text(p, line)

# --- Markown to Doc (For Chat) ---
def add_markdown_to_doc(doc, text):
    """Parses markdown text (bold, bullets, tables) into Word elements."""
lines = text.split('\n')
table_row_pattern = re.compile(r"^\|(.+)\|")
table_sep_pattern = re.compile(r"^\|[-:| ]+\|")
@@ -288,8 +325,6 @@ def add_markdown_to_doc(doc, text):

if stripped.startswith('##'):
p = doc.add_heading(stripped.lstrip('#').strip(), level=2)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
elif stripped.startswith('*') or stripped.startswith('-'):
clean_text = stripped.lstrip('*- ').strip()
p = doc.add_paragraph(style='List Bullet')
@@ -298,8 +333,7 @@ def add_markdown_to_doc(doc, text):
p = doc.add_paragraph()
_add_rich_text(p, stripped)

    if table_data:
        _render_word_table(doc, table_data)
    if table_data: _render_word_table(doc, table_data)

def _render_word_table(doc, rows):
if not rows: return
@@ -311,775 +345,425 @@ def _render_word_table(doc, rows):
for j, text in enumerate(row_data):
if j < len(row_cells):
p = row_cells[j].paragraphs[0]
                run = p.add_run(text)
                if i == 0: run.bold = True
                _add_rich_text(p, text)
                if i == 0: 
                    for run in p.runs: run.bold = True
doc.add_paragraph("")

def _add_rich_text(paragraph, text):
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            paragraph.add_run(part)

# --- AI VISUAL METADATA EXTRACTION ---
# --- METADATA EXTRACTION ---
def get_visual_metadata(file_path):
    """
    Uses Gemini Vision to read:
    1. Date & Time
    2. Meeting Title (Center text)
    3. Venue (Corner text)
    Returns a dict with keys: datetime_sg, duration, title, venue
    """
if shutil.which("ffmpeg") is None: return None
    
thumbnail_path = "temp_thumb.jpg"
    result_data = {
        "datetime_sg": None,
        "duration": 0,
        "title": "Meeting_Minutes",
        "venue": ""
    }

    result_data = {"datetime_sg": None, "duration": 0, "title": "Meeting_Minutes", "venue": ""}
try:
        # A. Get Duration using ffprobe
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                result_data["duration"] = float(result.stdout.strip())
            except: pass
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0: result_data["duration"] = float(res.stdout.strip())

        # B. Get Visuals using Vision
        subprocess.run([
            'ffmpeg', '-i', file_path, '-ss', '00:00:01', 
            '-vframes', '1', '-q:v', '2', '-y', thumbnail_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-i', file_path, '-ss', '00:00:01', '-vframes', '1', '-q:v', '2', '-y', thumbnail_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if os.path.exists(thumbnail_path):
            vision_model = genai.GenerativeModel('gemini-2.5-flash-lite')
            with open(thumbnail_path, "rb") as img_file:
                img_data = img_file.read()

            prompt = """
            Analyze this meeting screenshot. Return a JSON object with these keys:
            - "datetime": The date and time shown (format YYYY-MM-DD HH:MM).
            - "title": The large central text indicating the meeting name (e.g. 'Company A x Company B').
            - "venue": The platform name usually in the top right/left corner (e.g. 'Microsoft Teams', 'Zoom').
            vision = genai.GenerativeModel('gemini-2.5-flash-lite')
            with open(thumbnail_path, "rb") as img: img_data = img.read()

            If any value is not found, return "None" for that value.
            Return ONLY raw JSON.
            """
            
            response = vision_model.generate_content([
                {'mime_type': 'image/jpeg', 'data': img_data}, 
                prompt
            ])
            prompt = """Analyze this meeting screenshot. Return JSON:
            { "datetime": "YYYY-MM-DD HH:MM", "title": "Center Text", "venue": "Corner Text" }
            If not found, use "None"."""

            resp = vision.generate_content([{'mime_type': 'image/jpeg', 'data': img_data}, prompt])
try:
                text = response.text.strip().replace("```json", "").replace("```", "")
                data = json.loads(text)
                
                if data.get("title") and data["title"] != "None":
                    result_data["title"] = data["title"].replace(" ", "_").replace("/", "-") # Sanitize for filename
                
                if data.get("venue") and data["venue"] != "None":
                    result_data["venue"] = data["venue"]
                    
                dt_str = data.get("datetime")
                if dt_str and dt_str != "None":
                     dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                     dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
                     sg_tz = pytz.timezone('Asia/Singapore')
                     result_data["datetime_sg"] = dt_obj.astimezone(sg_tz)
            except Exception as e:
                print(f"JSON Parse Error: {e}")

    except Exception as e:
        print(f"Visual Metadata Error: {e}")
                data = json.loads(resp.text.strip().replace("```json", "").replace("```", ""))
                if data.get("title") != "None": result_data["title"] = data["title"].replace(" ", "_")
                if data.get("venue") != "None": result_data["venue"] = data["venue"]
                if data.get("datetime") != "None":
                    dt = datetime.datetime.strptime(data["datetime"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
                    result_data["datetime_sg"] = dt.astimezone(pytz.timezone('Asia/Singapore'))
            except: pass
    except: pass
finally:
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
return result_data

# --- Standard Helpers ---

def get_basecamp_session_user():
    if not st.session_state.basecamp_token: return None
    session = OAuth2Session(BASECAMP_CLIENT_ID, token=st.session_state.basecamp_token)
    session.headers.update(BASECAMP_USER_AGENT)
    return session

def upload_to_gcs(file_path, destination_blob_name):
# --- Drive & Cloud Helpers ---
def upload_to_gcs(file_path, blob_name):
try:
bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob = bucket.blob(blob_name)
blob.upload_from_filename(file_path, timeout=3600)
        return f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
    except Exception as e:
        st.error(f"GCS Upload Error: {e}")
        return None
        return f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    except: return None

def get_or_create_folder(service, folder_name):
def get_or_create_folder(service, name):
try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        q = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
        res = service.files().list(q=q, fields="files(id)").execute()
        items = res.get('files', [])
if items: return items[0]['id']
else:
            file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
    except Exception as e: return None
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
            return service.files().create(body=meta, fields='id').execute().get('id')
    except: return None

def upload_to_drive_user(file_stream, file_name, target_folder_name):
def upload_to_drive_user(file, name, folder):
if not st.session_state.gdrive_creds: return None
try:
service = build("drive", "v3", credentials=st.session_state.gdrive_creds)
        folder_id = get_or_create_folder(service, target_folder_name)
        parents = [folder_id] if folder_id else []

        file_metadata = {"name": file_name, "parents": parents}
        media = MediaIoBaseUpload(
            file_stream, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        file = service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        return file.get("id")
    except Exception as e:
        st.error(f"Google Drive Upload Error: {e}")
        return None
        fid = get_or_create_folder(service, folder)
        meta = {"name": name, "parents": [fid] if fid else []}
        media = MediaIoBaseUpload(file, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        return service.files().create(body=meta, media_body=media, fields="id").execute().get("id")
    except: return None

def save_analysis_data_to_drive(data_dict, filename):
def save_analysis_data_to_drive(data, filename):
if not st.session_state.gdrive_creds: return None
try:
service = build("drive", "v3", credentials=st.session_state.gdrive_creds)
        folder_id = get_or_create_folder(service, "Meeting_Data")
        if not folder_id: return None

        json_str = json.dumps(data_dict, indent=2)
        fh = io.BytesIO(json_str.encode('utf-8'))
        file_metadata = {"name": filename, "parents": [folder_id]}
        fid = get_or_create_folder(service, "Meeting_Data")
        fh = io.BytesIO(json.dumps(data, indent=2).encode('utf-8'))
        meta = {"name": filename, "parents": [fid] if fid else []}
media = MediaIoBaseUpload(fh, mimetype='application/json')
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return file.get("id")
    except Exception as e: return None
        return service.files().create(body=meta, media_body=media, fields="id").execute().get("id")
    except: return None

def list_past_meetings():
if not st.session_state.gdrive_creds: return []
try:
service = build("drive", "v3", credentials=st.session_state.gdrive_creds)
        folder_id = get_or_create_folder(service, "Meeting_Data")
        if not folder_id: return []
        query = f"'{folder_id}' in parents and mimeType='application/json' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, createdTime)", orderBy="createdTime desc").execute()
        return results.get('files', [])
        fid = get_or_create_folder(service, "Meeting_Data")
        if not fid: return []
        q = f"'{fid}' in parents and mimeType='application/json' and trashed=false"
        return service.files().list(q=q, fields="files(id, name, createdTime)", orderBy="createdTime desc").execute().get('files', [])
except: return []

def load_meeting_data(file_id):
if not st.session_state.gdrive_creds: return None
try:
service = build("drive", "v3", credentials=st.session_state.gdrive_creds)
        request = service.files().get_media(fileId=file_id)
fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        downloader = MediaIoBaseDownload(fh, service.files().get_media(fileId=file_id))
done = False
        while done is False:
            status, done = downloader.next_chunk()
        while not done: _, done = downloader.next_chunk()
fh.seek(0)
return json.load(fh)
    except Exception as e: return None
    except: return None

def get_basecamp_projects(_session):
    try:
        response = _session.get(f"{BASECAMP_API_BASE}/projects.json")
        response.raise_for_status()
        return sorted([(p['name'], p['id']) for p in response.json() if p['status'] == 'active'], key=lambda x: x[0])
# --- Basecamp Helpers ---
def get_bc_session():
    if not st.session_state.basecamp_token: return None
    s = OAuth2Session(BASECAMP_CLIENT_ID, token=st.session_state.basecamp_token)
    s.headers.update(BASECAMP_USER_AGENT)
    return s

def get_bc_projects(sess):
    try: return sorted([(p['name'], p['id']) for p in sess.get(f"{BASECAMP_API_BASE}/projects.json").json() if p['status']=='active'], key=lambda x:x[0])
except: return []

def get_project_tools(_session, project_id):
    try:
        response = _session.get(f"{BASECAMP_API_BASE}/projects/{project_id}.json")
        response.raise_for_status()
        return response.json().get('dock', [])
def get_bc_dock(sess, pid):
    try: return sess.get(f"{BASECAMP_API_BASE}/projects/{pid}.json").json().get('dock', [])
except: return []

def get_todolists(_session, todoset_id, project_id):
    try:
        url = f"{BASECAMP_API_BASE}/buckets/{project_id}/todosets/{todoset_id}/todolists.json"
        resp = _session.get(url)
        return sorted([(t['title'], t['id']) for t in resp.json()], key=lambda x: x[0])
def get_bc_lists(sess, tid, pid):
    try: return sorted([(t['title'], t['id']) for t in sess.get(f"{BASECAMP_API_BASE}/buckets/{pid}/todosets/{tid}/todolists.json").json()], key=lambda x:x[0])
except: return []

def upload_bc_attachment(_session, file_bytes, file_name):
def upload_bc_file(sess, data, name):
try:
        headers = _session.headers.copy()
        headers.update({'Content-Type': 'application/octet-stream', 'Content-Length': str(len(file_bytes))})
        resp = _session.post(f"{BASECAMP_API_BASE}/attachments.json?name={file_name}", data=file_bytes, headers=headers)
        return resp.json()['attachable_sgid']
    except Exception as e:
        st.error(f"Basecamp Upload Error: {e}")
        return None
        h = sess.headers.copy(); h.update({'Content-Type': 'application/octet-stream', 'Content-Length': str(len(data))})
        return sess.post(f"{BASECAMP_API_BASE}/attachments.json?name={name}", data=data, headers=h).json()['attachable_sgid']
    except: return None

def post_to_basecamp(_session, project_id, tool_type, tool_id, sub_id, title, content, attachment_sgid):
def post_to_bc(sess, pid, tool, tid, subid, title, body, sgid):
try:
        attach_html = f'<bc-attachment sgid="{attachment_sgid}"></bc-attachment>' if attachment_sgid else ""
        
        if tool_type == "To-dos":
            url = f"{BASECAMP_API_BASE}/buckets/{project_id}/todolists/{sub_id}/todos.json"
            payload = {"content": title, "description": content + attach_html}
        elif tool_type == "Message Board":
            url = f"{BASECAMP_API_BASE}/buckets/{project_id}/message_boards/{tool_id}/messages.json"
            payload = {"subject": title, "content": content + attach_html, "status": "active"}
        elif tool_type == "Docs & Files":
            url = f"{BASECAMP_API_BASE}/buckets/{project_id}/vaults/{tool_id}/uploads.json"
            payload = {"attachable_sgid": attachment_sgid, "base_name": title, "content": content}

        resp = _session.post(url, json=payload)
        resp.raise_for_status()
        att = f'<bc-attachment sgid="{sgid}"></bc-attachment>' if sgid else ""
        if tool == "To-dos":
            url, pl = f"{BASECAMP_API_BASE}/buckets/{pid}/todolists/{subid}/todos.json", {"content": title, "description": body + att}
        elif tool == "Message Board":
            url, pl = f"{BASECAMP_API_BASE}/buckets/{pid}/message_boards/{tid}/messages.json", {"subject": title, "content": body + att, "status": "active"}
        elif tool == "Docs & Files":
            url, pl = f"{BASECAMP_API_BASE}/buckets/{pid}/vaults/{tid}/uploads.json", {"attachable_sgid": sgid, "base_name": title, "content": body}
        sess.post(url, json=pl).raise_for_status()
return True
    except Exception as e:
        st.error(f"Basecamp Post Error: {e}")
        return False
    except: return False

def get_structured_notes_google(audio_file_path, file_name, participants_context):
def analyze_audio_gemini(path, participants):
try:
        with st.spinner(f"Converting {file_name} to audio-only FLAC..."):
            base_name = os.path.splitext(audio_file_path)[0]
            flac_file_path = f"{base_name}.flac"
            command = ["ffmpeg", "-i", audio_file_path, "-vn", "-acodec", "flac", "-y", flac_file_path]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with st.spinner(f"Uploading converted audio to Google Cloud Storage..."):
            flac_blob_name = f"{os.path.splitext(file_name)[0]}.flac"
            gcs_uri = upload_to_gcs(flac_file_path, flac_blob_name)
            if not gcs_uri: return {"error": "Upload failed."}

        progress_text = "Transcribing & identifying speakers..."
        progress_bar = st.progress(0, text=progress_text)
        
        audio = speech.RecognitionAudio(uri=gcs_uri)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
            language_code="en-US",
            enable_automatic_punctuation=True,
            use_enhanced=True,
            model="video",
            diarization_config=speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True,
                min_speaker_count=2,
                max_speaker_count=6
            )
        )
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        with st.spinner("Converting..."):
            subprocess.run(['ffmpeg', '-i', path, '-vn', '-acodec', 'flac', '-y', f"{path}.flac"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        while not operation.done():
            metadata = operation.metadata
            if metadata and metadata.progress_percent:
                progress_bar.progress(metadata.progress_percent, text=f"Transcribing: {metadata.progress_percent}%")
            time.sleep(2)

        progress_bar.progress(100, text="Transcription Complete")
        response = operation.result(timeout=3600)
        progress_bar.empty()

        if not response.results:
             return {"error": "Transcription failed. The audio might be silent."}

        result = response.results[-1]
        words_info = result.alternatives[0].words
        full_transcript_text = ""
        current_speaker = -1
        for word_info in words_info:
            if word_info.speaker_tag != current_speaker:
                current_speaker = word_info.speaker_tag
                full_transcript_text += f"\n\nSpeaker {current_speaker}: "
            full_transcript_text += word_info.word + " "
        if not full_transcript_text.strip():
            full_transcript_text = " ".join([result.alternatives[0].transcript for result in response.results])

        with st.spinner("Analyzing conversation & matching names..."):
            # --- SUPER SPECIFIC ACTION PROMPT ---
            prompt = f"""
            You are an expert meeting secretary. 
            Here is the context of who was in the meeting:
            {participants_context}
            The transcript below uses "Speaker 1", "Speaker 2", etc.
            Your job is to figure out which Speaker matches which Name from the list above.
            Transcript:
            {full_transcript_text}
            ---
            YOUR TASKS:
            1. RECONSTRUCTION: When writing the notes, DO NOT use "Speaker 1". Use their REAL NAMES (e.g., "John said...").
            2. EXTRACTION:
            ## DISCUSSION ##
            Summarize main points using the real names.
            FORMAT:
            ## Section Title (e.g., ## Content and Grammar)
            * **Wording & Tone:** John requested avoiding the casual use of "You are".
            * Bullet point 3.
            (Leave a blank line between sections)
        with st.spinner("Uploading..."):
            uri = upload_to_gcs(f"{path}.flac", f"{os.path.basename(path)}.flac")
            if not uri: return {"error": "Upload failed"}

        with st.spinner("Transcribing..."):
            client = speech.SpeechClient(credentials=service_account.Credentials.from_service_account_info(GCP_SERVICE_ACCOUNT_JSON))
            audio = speech.RecognitionAudio(uri=uri)
            config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.FLAC, language_code="en-US", enable_automatic_punctuation=True, use_enhanced=True, model="video", diarization_config=speech.SpeakerDiarizationConfig(enable_speaker_diarization=True, min_speaker_count=2, max_speaker_count=6))
            op = client.long_running_recognize(config=config, audio=audio)
            res = op.result(timeout=3600)

            ## NEXT STEPS ##
            List highly specific, actionable items. **DO NOT MISS ANY TASKS.**
            FORMAT:
            * **[Assigned Name]**: [Action Verb] [Specific Details] - Due: [Time if mentioned]
            transcript = ""
            cur_spk = -1
            for w in res.results[-1].alternatives[0].words:
                if w.speaker_tag != cur_spk:
                    cur_spk = w.speaker_tag
                    transcript += f"\n\nSpeaker {cur_spk}: "
                transcript += w.word + " "

            ## CLIENT REQUESTS ##
            List specific questions or requests asked BY the Client.
            FORMAT:
            * Bullet point 1.
        with st.spinner("Analyzing..."):
            prompt = f"""
            Role: Expert Meeting Secretary.
            Context: {participants}
            Transcript: {transcript}
            
            Tasks:
            1. Identify speakers.
            2. Create structured sections:
               ## OVERVIEW ##
               [Brief summary of WHO met and WHAT was discussed - 2-3 sentences]
               
               ## DISCUSSION ##
               [Detailed bullet points with headers]
               
               ## NEXT STEPS ##
               [Specific actions: * **Name**: Action - Deadline]
               
               ## CLIENT REQUESTS ##
               [Requests from client]
           """
            response = gemini_model.generate_content(prompt)
            text = response.text
            resp = gemini_model.generate_content(prompt).text

            discussion = ""
            next_steps = ""
            client_reqs = ""
            # Parsing
            ov, disc, next_s, creq = "", "", "", ""
try:
                if "## DISCUSSION ##" in text:
                    discussion = text.split("## DISCUSSION ##")[1].split("## NEXT STEPS ##")[0].strip()
                if "## NEXT STEPS ##" in text:
                    next_steps = text.split("## NEXT STEPS ##")[1].split("## CLIENT REQUESTS ##")[0].strip()
                if "## CLIENT REQUESTS ##" in text:
                    client_reqs = text.split("## CLIENT REQUESTS ##")[1].strip()
                if not discussion: discussion = text
            except:
                discussion = text
                if "## OVERVIEW ##" in resp: ov = resp.split("## OVERVIEW ##")[1].split("## DISCUSSION ##")[0].strip()
                if "## DISCUSSION ##" in resp: disc = resp.split("## DISCUSSION ##")[1].split("## NEXT STEPS ##")[0].strip()
                if "## NEXT STEPS ##" in resp: next_s = resp.split("## NEXT STEPS ##")[1].split("## CLIENT REQUESTS ##")[0].strip()
                if "## CLIENT REQUESTS ##" in resp: creq = resp.split("## CLIENT REQUESTS ##")[1].strip()
            except: disc = resp

            return {
                "discussion": discussion,
                "next_steps": next_steps,
                "client_reqs": client_reqs,
                "full_transcript": full_transcript_text
            }
    except Exception as e:
        return {"error": str(e)}
            return {"overview": ov, "discussion": disc, "next_steps": next_s, "client_reqs": creq, "full_transcript": transcript}
            
    except Exception as e: return {"error": str(e)}
finally:
        try:
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            bucket.blob(flac_blob_name).delete()
        try: storage_client.bucket(GCS_BUCKET_NAME).blob(f"{os.path.basename(path)}.flac").delete()
except: pass

def add_formatted_text(cell, text):
    """Original simple parser for main doc."""
    cell.text = ""
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        if line.startswith('##'):
            run = p.add_run(line.strip('#').strip())
            run.underline = True
        elif line.startswith('*'):
            clean = line.lstrip('*').lstrip("•").strip()
            if clean.startswith('**') and ':**' in clean:
                try:
                    parts = clean.split(':**', 1)
                    p.text = "•\t"
                    p.add_run(parts[0].lstrip('**').strip() + ": ").bold = True
                    p.add_run(parts[1].strip())
                    p.paragraph_format.left_indent = Inches(0.25)
                except:
                    p.text = f"•\t{clean}"
                    p.paragraph_format.left_indent = Inches(0.25)
            else:
                p.text = f"•\t{clean}"
                p.paragraph_format.left_indent = Inches(0.25)
        else:
            p.add_run(line)

# -----------------------------------------------------
# 8. STREAMLIT UI (MAIN)
# 8. MAIN UI
# -----------------------------------------------------
if 'ai_results' not in st.session_state:
    st.session_state.ai_results = {"discussion": "", "next_steps": "", "client_reqs": "", "full_transcript": ""}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "auto_client_reps" not in st.session_state:
    st.session_state.auto_client_reps = ""
if "auto_ifoundries_reps" not in st.session_state:
    st.session_state.auto_ifoundries_reps = ""
if "saved_participants_input" not in st.session_state:
    st.session_state.saved_participants_input = ""
# --- METADATA STATE ---
if 'detected_date' not in st.session_state:
    st.session_state.detected_date = None
if 'detected_time' not in st.session_state:
    st.session_state.detected_time = None
if 'detected_title' not in st.session_state:
    st.session_state.detected_title = "Meeting_Minutes"
if 'detected_venue' not in st.session_state:
    st.session_state.detected_venue = ""
if 'ai_results' not in st.session_state: st.session_state.ai_results = {}
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'saved_participants' not in st.session_state: st.session_state.saved_participants = ""

st.title("🤖 AI Meeting Manager")

tab1, tab2, tab3, tab4 = st.tabs(["1. Analyze", "2. Review & Export", "3. Chat", "4. History"])

with tab1:
    st.header("1. Analyze Audio")
    participants_input = st.text_area(
        "Known Participants (Teach the AI)", 
        value="Client's Exact Name (Client)\niFoundries Exact Name (iFoundries)",
        help="The AI will read this to match 'Speaker 1' to these names."
    )
    uploaded_file = st.file_uploader("Upload Meeting", type=["mp3", "mp4", "m4a", "wav"])
    st.header("1. Analyze")
    participants = st.text_area("Participants", "Client (Client)\niFoundries (iFoundries)")
    up = st.file_uploader("Upload", type=['mp3','mp4','m4a','wav'])

    if st.button("Analyze Audio"):
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name}") as tmp:
                tmp.write(uploaded_file.getvalue())
                path = tmp.name
            
            st.session_state.chat_history = [] 
            st.session_state.saved_participants_input = participants_input 
    if st.button("Analyze"):
        if up:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{up.name.split('.')[-1]}") as tmp:
                tmp.write(up.getvalue()); path = tmp.name

            # --- METADATA EXTRACTION ---
            with st.spinner("🕵️‍♀️ Detecting details from screen..."):
                metadata = get_visual_metadata(path)
            # 1. Get Metadata
            with st.spinner("Extracting Metadata..."):
                meta = get_visual_metadata(path)
                st.session_state.detected_date = meta['datetime_sg'].date() if meta['datetime_sg'] else datetime.date.today()

            if metadata and metadata['datetime_sg']:
                real_start_time = metadata['datetime_sg']
                duration_secs = metadata['duration']
                # Time Range logic
                if meta['datetime_sg'] and meta['duration']:
                    end = meta['datetime_sg'] + datetime.timedelta(seconds=meta['duration'])
                    st.session_state.detected_time = f"{meta['datetime_sg'].strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
                else: st.session_state.detected_time = "Unknown"

                st.session_state.detected_date = real_start_time.date()
                
                # Calculate End Time
                end_time = real_start_time + datetime.timedelta(seconds=duration_secs)
                time_str = f"{real_start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
                st.session_state.detected_time = time_str
                
                if metadata['title']: st.session_state.detected_title = metadata['title']
                if metadata['venue']: st.session_state.detected_venue = metadata['venue']
                
                st.toast(f"📅 Found: {st.session_state.detected_date} | {metadata.get('title')} | {metadata.get('venue')}")
            else:
                st.toast("⚠️ Metadata not found. Using defaults.")

            c_list = [l.replace("(Client)","").strip() for l in participants_input.split('\n') if "(Client)" in l]
            i_list = [l.replace("(iFoundries)","").strip() for l in participants_input.split('\n') if "(iFoundries)" in l]
            st.session_state.auto_client_reps = "\n".join(c_list)
            st.session_state.auto_ifoundries_reps = ", ".join(i_list)
                st.session_state.detected_title = meta['title'] if meta['title'] else "Meeting"
                st.session_state.detected_venue = meta['venue'] if meta['venue'] else ""
            
            # 2. Analyze
            st.session_state.saved_participants = participants
            res = analyze_audio_gemini(path, participants)

            res = get_structured_notes_google(path, uploaded_file.name, participants_input)
if "error" in res: st.error(res["error"])
            else: 
            else:
st.session_state.ai_results = res
                
                # Auto-Save to History (Include Chat History if any, usually empty here)
if st.session_state.gdrive_creds:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
save_data = {
                        "ai_results": res,
                        "participants": participants_input,
                        "date": timestamp,
                        "detected_title": st.session_state.detected_title
                        "ai_results": res, 
                        "participants": participants, 
                        "date": str(datetime.datetime.now()),
                        "chat_history": [] # Init empty chat history
}
                    fname = f"Data_{uploaded_file.name}_{timestamp}.json"
                    if save_analysis_data_to_drive(save_data, fname):
                        st.toast("💾 Meeting data saved to Drive History!")

                st.success("Analysis Complete!")
        else:
            st.warning("Please upload a file first.")
                    save_analysis_data_to_drive(save_data, f"Data_{up.name}_{datetime.datetime.now().strftime('%Y%m%d')}.json")
                
                # Auto-Fill Reps
                cl = [l for l in participants.split('\n') if "(Client)" in l]
                il = [l for l in participants.split('\n') if "(iFoundries)" in l]
                st.session_state.crep = "\n".join(cl)
                st.session_state.irep = "\n".join(il)
                
                st.success("Done! Go to Review tab.")

with tab2:
    st.header("2. Review Notes")
    
    sg_tz = pytz.timezone('Asia/Singapore')
    sg_now = datetime.datetime.now(sg_tz)
    
    st.header("2. Review")
# Defaults
    default_date = st.session_state.detected_date if st.session_state.detected_date else sg_now.date()
    default_time = st.session_state.detected_time if st.session_state.detected_time else sg_now.strftime("%I:%M %p")
    default_venue = st.session_state.detected_venue if st.session_state.detected_venue else ""
    d_date = st.session_state.get('detected_date', datetime.date.today())
    d_time = st.session_state.get('detected_time', "")
    d_venue = st.session_state.get('detected_venue', "")

    # Intelligent Filename
    base_title = st.session_state.detected_title if st.session_state.detected_title else "Meeting_Minutes"
    final_fname = f"{base_title.replace('_',' ')} - {default_date}.docx"

    row1, row2 = st.columns(2)
    with row1:
        date_obj = st.date_input("Date", default_date)
        venue = st.text_input("Venue", value=default_venue)
        client_rep = st.text_area("Client Reps", value=st.session_state.auto_client_reps)
        absent = st.text_input("Absent")
    with row2:
        time_obj = st.text_input("Time", value=default_time)
        default_prepared_by = st.session_state.user_real_name if st.session_state.user_real_name else st.session_state.auto_ifoundries_reps
        prepared_by = st.text_input("Prepared by", value=default_prepared_by)
        ifoundries_rep = st.text_input("iFoundries Reps", value=st.session_state.auto_ifoundries_reps)
    c1, c2 = st.columns(2)
    date = c1.date_input("Date", d_date)
    venue = c1.text_input("Venue", d_venue)
    crep = c1.text_input("Client Reps", st.session_state.get('crep',''))
    absent = c1.text_input("Absent")

    date_str = date_obj.strftime("%d %B %Y") if date_obj else ""
    time_str = time_obj
    time_str = c2.text_input("Time", d_time)
    prep = c2.text_input("Prepared By", st.session_state.user_real_name)
    irep = c2.text_input("iFoundries Reps", st.session_state.get('irep',''))
    
    st.subheader("Content")
    overview = st.text_area("Overview", st.session_state.ai_results.get("overview", ""))
    disc = st.text_area("Discussion", st.session_state.ai_results.get("discussion", ""), height=300)
    next_s = st.text_area("Next Steps", st.session_state.ai_results.get("next_steps", ""), height=150)

    discussion_text = st.text_area("Discussion", value=st.session_state.ai_results.get("discussion", ""), height=300)
    next_steps_text = st.text_area("Next Steps", value=st.session_state.ai_results.get("next_steps", ""), height=200)
    with st.expander("View Specific Client Requests"):
        st.text_area("Client Requests", value=st.session_state.ai_results.get("client_reqs", ""), height=150)

st.divider()
    st.header("3. Generate & Upload")
    do_d = st.checkbox("Drive", True)
    do_b = st.checkbox("Basecamp")

    bc_session_user = None
    bc_project_id = None
    bc_tool_type = None 
    bc_tool_id = None 
    bc_sub_id = None 
    bc_title = ""
    bc_content = ""

    do_drive = st.checkbox("Upload to Drive")
    do_basecamp = st.checkbox("Upload to Basecamp") 

    if do_basecamp:
        bc_session_user = get_basecamp_session_user()
        try:
            projects_list = get_basecamp_projects(bc_session_user)
            if not projects_list:
                st.warning("No active Basecamp projects found.")
            else:
                selected_project_name = st.selectbox("Select Project", options=[p[0] for p in projects_list], index=None, placeholder="Choose...")
                
                if selected_project_name:
                    bc_project_id = next(p[1] for p in projects_list if p[0] == selected_project_name)
                    bc_tool_type = st.selectbox("Where to post?", ["To-dos", "Message Board", "Docs & Files"], index=0)
                    project_tools = get_project_tools(bc_session_user, bc_project_id)
                    
                    if bc_tool_type == "To-dos":
                        todoset = next((t for t in project_tools if t['name'] == 'todoset'), None)
                        if todoset:
                            bc_tool_id = todoset['id']
                            todolists = get_todolists(bc_session_user, todoset['id'], bc_project_id)
                            if todolists:
                                selected_list = st.selectbox("Select Todo List", options=[tl[0] for tl in todolists])
                                if selected_list:
                                    bc_sub_id = next(tl[1] for tl in todolists if tl[0] == selected_list)
                                    bc_title = st.text_input("To-Do Title", value=f"{base_title.replace('_',' ')} - {date_str}")
                                    bc_content = st.text_area("Description", value="Attached are the minutes from the meeting.")
                            else: st.warning("No To-do lists found.")
                    
                    elif bc_tool_type == "Message Board":
                        mb = next((t for t in project_tools if t['name'] == 'message_board'), None)
                        if mb:
                            bc_tool_id = mb['id']
                            bc_title = st.text_input("Subject", value=f"{base_title.replace('_',' ')} - {date_str}")
                            bc_content = st.text_area("Message Body", value="Hi team,\n\nHere are the minutes from today's meeting.")
                    
                    elif bc_tool_type == "Docs & Files":
                        vault = next((t for t in project_tools if t['name'] == 'vault'), None)
                        if vault:
                            bc_tool_id = vault['id']
                            bc_title = st.text_input("File Name", value=final_fname)
                            bc_content = st.text_area("Description (Optional)", value="")
                            
        except Exception as e: st.error(f"Basecamp Error: {e}")

    if st.button("Generate Word Doc"):
        basecamp_ready = True
        if do_basecamp:
            if not bc_project_id:
                st.error("Please select a project.")
                basecamp_ready = False
            elif bc_tool_type == "To-dos" and not bc_sub_id:
                st.error("Please select a To-do List.")
                basecamp_ready = False

        if not date_str or not prepared_by or not client_rep:
            st.error("Missing required fields (*)")
        elif not do_basecamp or basecamp_ready:
            try:
                doc = Document("Minutes Of Meeting - Template.docx")
                
                # --- 1. REPLACE TITLE ---
                for p in doc.paragraphs:
                    if "[Title]" in p.text:
                        p.text = p.text.replace("[Title]", base_title.replace('_',' '))

                # --- 2. FILL TABLE DATA ---
                t0 = doc.tables[0]
                t0.cell(1,1).text = date_str
                t0.cell(2,1).text = time_str
                t0.cell(3,1).text = venue
                c_rep_final = f"{client_rep} (Client)" if client_rep and "(Client)" not in client_rep else client_rep
                i_rep_final = f"{ifoundries_rep} (iFoundries)" if ifoundries_rep and "(iFoundries)" not in ifoundries_rep else ifoundries_rep
                t0.cell(4,1).text = c_rep_final
                t0.cell(4,2).text = i_rep_final
                t0.cell(5,1).text = absent

                # --- 3. INSERT OVERVIEW & DETAILS ---
                t1 = doc.tables[1]
                # Overview is typically the first row of the second table or specific cell
                # Assuming Row 2, Col 1 based on previous prompt (index 1,0 or 1,1 depending on template)
                # Let's target the Discussion cell for now as standard
                
                # Use Overview logic if available from AI results
                # (Assuming AI generates an "Overview" section, otherwise use Discussion)
                add_formatted_text(t1.cell(2,1), discussion_text)
                add_formatted_text(t1.cell(4,1), next_steps_text)
                
                # --- 4. ADJOURNMENT TIME ---
                # Find last row/cell often used for "Meeting adjourned at..."
                # We'll assume it's a specific cell or append it
                try:
                   end_time_only = time_str.split('-')[-1].strip()
                   t1.cell(5,1).text = f"Meeting adjourned at {end_time_only}"
                except: pass

                doc.paragraphs[-1].text = f"Prepared by: {prepared_by}"
                
                bio = io.BytesIO()
                doc.save(bio)
                bio.seek(0)
    pid, tool, tid, subid, btitle, bdesc = None, None, None, None, "", ""
    
    if do_b:
        sess = get_basecamp_session_user()
        projs = get_basecamp_projects(sess)
        pname = st.selectbox("Project", [p[0] for p in projs])
        if pname:
            pid = next(p[1] for p in projs if p[0]==pname)
            tool = st.selectbox("Tool", ["To-dos", "Message Board", "Docs & Files"])
            dock = get_project_tools(sess, pid)
            
            if tool == "To-dos":
                tid = next((t['id'] for t in dock if t['name']=='todoset'), None)
                lists = get_todolists(sess, tid, pid)
                lname = st.selectbox("List", [l[0] for l in lists])
                if lname: subid = next(l[1] for l in lists if l[0]==lname)
                btitle = st.text_input("Title", f"Minutes - {date}")
                bdesc = st.text_area("Desc", "Attached.")
            
            elif tool == "Message Board":
                tid = next((t['id'] for t in dock if t['name']=='message_board'), None)
                btitle = st.text_input("Subject", f"Minutes - {date}")
                bdesc = st.text_area("Body", "Attached.")

                if do_drive and st.session_state.gdrive_creds:
                    with st.spinner("Uploading to Drive ('Meeting Notes' folder)..."):
                        if upload_to_drive_user(bio, final_fname, "Meeting Notes"): st.success("✅ Uploaded to Drive!")
                        else: st.error("Drive upload failed.")
                    bio.seek(0)
            elif tool == "Docs & Files":
                tid = next((t['id'] for t in dock if t['name']=='vault'), None)
                btitle = st.text_input("File Name", f"Minutes_{date}.docx")

                if do_basecamp and basecamp_ready and bc_session_user:
                    with st.spinner(f"Posting to Basecamp ({bc_tool_type})..."):
                        file_bytes = bio.getvalue()
                        sgid = upload_bc_attachment(bc_session_user, file_bytes, final_fname)
                        if sgid:
                            if post_to_basecamp(bc_session_user, bc_project_id, bc_tool_type, bc_tool_id, bc_sub_id, bc_title, bc_content, sgid):
                                st.success(f"✅ Posted to Basecamp!")
                            else: st.error("Basecamp post failed.")
                        else: st.error("Basecamp upload failed.")
                    bio.seek(0)

                st.download_button("Download .docx", bio, final_fname)
                
            except Exception as e:
                st.error(f"Error: {e}")
    if st.button("Generate"):
        doc = Document("Minutes Of Meeting - Template.docx")
        
        # 1. Title Replace
        for p in doc.paragraphs: 
            if "[Title]" in p.text: p.text = p.text.replace("[Title]", st.session_state.get("detected_title", "Meeting"))
            
        # 2. Header Table
        t = doc.tables[0]
        t.cell(1,1).text = str(date)
        t.cell(2,1).text = str(time_str)
        t.cell(3,1).text = venue
        t.cell(4,1).text = crep
        t.cell(4,2).text = irep
        t.cell(5,1).text = absent
        
        # 3. Content Table
        t2 = doc.tables[1]
        t2.cell(1,1).text = overview # Overview in Green Box
        add_formatted_text(t2.cell(2,1), disc)
        add_formatted_text(t2.cell(4,1), next_s)
        
        # 4. Adjourned Time
        try: end_t = time_str.split('-')[1].strip()
        except: end_t = "Unknown"
        t2.cell(5,1).text = f"Meeting adjourned at {end_t}"
        
        doc.paragraphs[-1].text = f"Prepared by: {prep}"
        
        b = io.BytesIO(); doc.save(b); b.seek(0)
        fn = f"{st.session_state.get('detected_title','Minutes')}_{date}.docx"
        
        if do_d: upload_to_drive_user(b, fn, "Meeting Notes")
        if do_b and pid:
            sgid = upload_bc_attachment(sess, b.getvalue(), fn)
            post_to_bc(sess, pid, tool, tid, subid, btitle, bdesc, sgid)
            
        st.success("Done!")

with tab3:
    st.header("💬 Chat with your Meeting")
    
    transcript_context = st.session_state.ai_results.get("full_transcript", "")
    participants_context = st.session_state.saved_participants_input
    st.header("Chat")

    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("💾 Save Chat to Drive"):
            if not st.session_state.gdrive_creds:
                st.error("Please login to Drive first!")
            elif not st.session_state.chat_history:
                st.warning("No chat history to save.")
            else:
                try:
                    chat_doc = Document()
                    chat_doc.add_heading(f"AI Chat Log - {date_str}", 0)
                    for msg in st.session_state.chat_history:
                        role = "AI Assistant" if msg["role"] == "assistant" else "User"
                        p = chat_doc.add_paragraph()
                        p.add_run(f"{role}: ").bold = True
                        add_markdown_to_doc(chat_doc, msg["content"])
                        chat_doc.add_paragraph("_" * 50)

                    chat_bio = io.BytesIO()
                    chat_doc.save(chat_bio)
                    chat_bio.seek(0)
                    chat_fname = f"AI_{st.session_state.detected_title}_{date_str}.docx"
                    
                    with st.spinner("Saving chat log..."):
                        if upload_to_drive_user(chat_bio, chat_fname, "Chats"):
                            st.success(f"✅ Saved to 'Chats' folder in Drive!")
                        else: st.error("Failed to save chat.")
                except Exception as e: st.error(f"Error saving chat: {e}")

    if not transcript_context:
        st.info("⚠️ Please upload and analyze a meeting audio file in Tab 1 first.")
    else:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

        chat_container = st.container(height=500)
    # Save Chat Logic
    if st.button("💾 Save Chat to Drive"):
        d = Document()
        d.add_heading(f"Chat Log - {datetime.date.today()}", 0)
        for m in st.session_state.chat_history:
            p = d.add_paragraph()
            role = "AI" if m['role'] == 'assistant' else "User"
            p.add_run(f"{role}: ").bold = True
            add_markdown_to_doc(d, m['content']) # Smart Markdown Parsing
            d.add_paragraph("_"*30)

        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(message["content"])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(message["content"])
        b = io.BytesIO(); d.save(b); b.seek(0)
        upload_to_drive_user(b, f"Chat_{st.session_state.get('detected_title','Log')}.docx", "Chats")
        st.success("Saved!")

        if prompt := st.chat_input("Ask a question about the meeting..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
    # Chat Loop
    for m in st.session_state.chat_history:
        st.chat_message(m["role"]).markdown(m["content"])
        
    if p := st.chat_input():
        st.session_state.chat_history.append({"role":"user", "content":p})
        st.chat_message("user").markdown(p)
        
        with st.chat_message("assistant"):
            # Stream logic
            def str_gen():
                prompt = f"""
                Context: {st.session_state.saved_participants}
                Transcript: {st.session_state.ai_results.get('full_transcript','')}
                Question: {p}
                Rules: Be professional. Use names. Be concise.
                """
                for chunk in gemini_model.generate_content(prompt, stream=True):
                    if chunk.text: yield chunk.text

            with chat_container:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant", avatar="🤖"):
                    def stream_text(response_iterator):
                        for chunk in response_iterator:
                            if chunk.parts:
                                yield chunk.text

                    try:
                        full_prompt = f"""
                        You are an efficient, action-oriented meeting secretary.
                        CONTEXT: {participants_context}
                        TRANSCRIPT: {transcript_context}
                        USER QUESTION: {prompt}
                        STRICT RULES:
                        1. Passive/Professional Voice.
                        2. No Speaker IDs.
                        3. Accuracy.
                        4. Conciseness.
                        """
                        stream_iterator = gemini_model.generate_content(full_prompt, stream=True)
                        response = st.write_stream(stream_text(stream_iterator))
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error("I couldn't generate a response. Please try again.")
            full_resp = st.write_stream(str_gen())
            st.session_state.chat_history.append({"role":"assistant", "content":full_resp})

with tab4:
    st.header("📂 Meeting History")
    st.caption("Load past meeting analysis to review notes or continue chatting.")
    st.header("History")
    if st.button("Refresh"): st.rerun()

    if not st.session_state.gdrive_creds:
        st.info("Please log in to Google Drive to access history.")
    else:
        if st.button("🔄 Refresh List"):
            st.rerun()

        files = list_past_meetings()
        
        if not files:
            st.warning("No past meeting data found in 'Meeting_Data' folder.")
        else:
            file_map = {f"{f['name']} ({f.get('createdTime', '')[:10]})": f['id'] for f in files}
            selected_file = st.selectbox("Select a past meeting:", options=list(file_map.keys()))
            
            if st.button("📂 Load Selected Meeting"):
                file_id = file_map[selected_file]
                with st.spinner("Loading meeting data..."):
                    data = load_meeting_data(file_id)
                    if data:
                        st.session_state.ai_results = data.get("ai_results", {})
                        st.session_state.saved_participants_input = data.get("participants", "")
                        # NEW: Restore detecting title/venue if saved
                        if "detected_title" in data: st.session_state.detected_title = data["detected_title"]
                        st.session_state.chat_history = [] 
                        
                        p_input = st.session_state.saved_participants_input
                        c_list = [l.replace("(Client)","").strip() for l in p_input.split('\n') if "(Client)" in l]
                        i_list = [l.replace("(iFoundries)","").strip() for l in p_input.split('\n') if "(iFoundries)" in l]
                        st.session_state.auto_client_reps = "\n".join(c_list)
                        st.session_state.auto_ifoundries_reps = ", ".join(i_list)

                        st.success("Meeting Loaded! Go to Tab 2 (Review) or Tab 3 (Chat).")
                        time.sleep(1)
                        st.rerun()
    files = list_past_meetings()
    if files:
        sel = st.selectbox("Select Meeting", [f['name'] for f in files])
        if st.button("Load"):
            fid = next(f['id'] for f in files if f['name'] == sel)
            data = load_meeting_data(fid)
            if data:
                st.session_state.ai_results = data.get("ai_results", {})
                st.session_state.saved_participants_input = data.get("participants", "")
                
                # RESTORE CHAT HISTORY
                st.session_state.chat_history = data.get("chat_history", [])
                
                # Restore Reps
                p_input = data.get("participants", "")
                c_list = [l.replace("(Client)","").strip() for l in p_input.split('\n') if "(Client)" in l]
                i_list = [l.replace("(iFoundries)","").strip() for l in p_input.split('\n') if "(iFoundries)" in l]
                st.session_state.auto_client_reps = "\n".join(c_list)
                st.session_state.auto_ifoundries_reps = ", ".join(i_list)
                
                st.success("Loaded! Check Tab 2 and 3.")
