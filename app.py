import os
import json
import io
from flask import Flask, redirect, url_for, session, request, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

app = Flask(__name__)
# Natively forces Flask to trust Render's proxy headers for incoming https traffic
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-kara-key")

# Requesting permission to see and read the specific vault file in Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_google_client_config():
    base_url = request.url_root.rstrip('/')
    return {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{base_url}/callback"]
        }
    }

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Kara | Balance of Wisdom</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f4f4f9; color: #333; }
        .container { max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        textarea { width: 100%; height: 100px; border-radius: 8px; padding: 12px; border: 1px solid #ccc; box-sizing: border-box; font-size: 16px; resize: vertical; }
        button { background: #2c3e50; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
        button:hover { background: #34495e; }
        .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 30px; }
        .ai-box { background: #fafafa; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; min-height: 200px; }
        h3 { margin-top: 0; border-bottom: 2px solid #2c3e50; padding-bottom: 8px; color: #2c3e50; }
        .login-box { text-align: center; padding: 50px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Kara</h1>
        
        {% if not logged_in %}
        <div class="login-box">
            <p>Welcome, Naseha and Alok. Connect your Google Drive to unlock the balance.</p>
            <a href="{{ url_for('login') }}"><button>Connect Google Drive</button></a>
        </div>
        {% else %}
        <form method="POST">
            <textarea name="question" placeholder="Ask the collective wisdom..."></textarea><br><br>
            <button type="submit">Weigh Responses</button>
        </form>
        
        {% if vault_status %}
        <p style="color: green; font-size: 14px;">✔ {{ vault_status }}</p>
        {% endif %}

        {% if results %}
        <div class="grid">
            <div class="ai-box"><h3>Gemini</h3><p>{{ results.gemini | safe }}</p></div>
            <div class="ai-box"><h3>Claude</h3><p>{{ results.claude | safe }}</p></div>
            <div class="ai-box"><h3>Grok</h3><p>{{ results.grok | safe }}</p></div>
        </div>
        {% endif %}
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    logged_in = 'credentials' in session
    results = None
    vault_status = "Connected to Google Drive. Secure session active."

    if logged_in and request.method == 'POST':
        question = request.form.get('question')
        
        try:
            # Re-assemble authorized credentials for this specific login session
            creds = Credentials(**session['credentials'])
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Locate the vault.json file across the Drive storage layers
            drive_results = drive_service.files().list(
                q="name = 'vault.json' and trashed = false",
                fields="files(id, name)"
            ).execute()
            items = drive_results.get('files', [])
            
            if not items:
                vault_status = "Error: vault.json file could not be located in your Google Drive."
                results = {
                    "gemini": "Unable to read keys.",
                    "claude": "Unable to read keys.",
                    "grok": "Unable to read keys."
                }
            else:
                # Target the file ID and stream its binary footprint into memory
                file_id = items[0]['id']
                drive_request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, drive_request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                # Unbox and decode the parsed structure
                vault_content = json.loads(fh.getvalue().decode('utf-8'))
                keys = vault_content.get("keys", {})
                
                # Confirm presence of keys inside the specific layout keys structure
                gemini_key = "Loaded Successfully ✔" if keys.get("gemini", {}).get("PSID") else "Missing ✘"
                claude_key = "Loaded Successfully ✔" if keys.get("claude", {}).get("sessionKey") else "Missing ✘"
                grok_key = "Loaded Successfully ✔" if keys.get("grok", {}).get("sso") else "Missing ✘"
                
                vault_status = "Connected to Google Drive. Secure session active. vault.json read complete."
                results = {
                    "gemini": f"<strong>Token State:</strong> {gemini_key}<br><br>Vault data parsed. Ready to connect browser engine pipeline for query: <em>{question}</em>",
                    "claude": f"<strong>Token State:</strong> {claude_key}<br><br>Vault data parsed. Ready to connect browser engine pipeline for query: <em>{question}</em>",
                    "grok": f"<strong>Token State:</strong> {grok_key}<br><br>Vault data parsed. Ready to connect browser engine pipeline for query: <em>{question}</em>"
                }
                
        except Exception as e:
            vault_status = f"Error reading Vault database: {str(e)}"
            results = {"gemini": "Error", "claude": "Error", "grok": "Error"}

    return render_template_string(HTML_TEMPLATE, logged_in=logged_in, results=results, vault_status=vault_status)

@app.route('/login')
def login():
    flow = Flow.from_client_config(
        get_google_client_config(),
        scopes=SCOPES,
        redirect_uri=f"{request.url_root.rstrip('/')}/callback"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    session['code_verifier'] = flow.code_verifier
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(
        get_google_client_config(),
        scopes=SCOPES,
        state=session.get('state'),
        redirect_uri=f"{request.url_root.rstrip('/')}/callback"
    )
    flow.fetch_token(
        authorization_response=request.url,
        code_verifier=session.get('code_verifier')
    )
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    session.pop('code_verifier', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
