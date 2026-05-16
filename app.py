import os
import json
from flask import Flask, redirect, url_for, session, request, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
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
    vault_status = None

    if logged_in:
        vault_status = "Connected to Google Drive. Secure session active."
        if request.method == 'POST':
            question = request.form.get('question')
            results = {
                "gemini": f"Gemini is primed with your session token. Ready to process: <em>{question}</em>",
                "claude": f"Claude is primed with your session token. Ready to process: <em>{question}</em>",
                "grok": f"Grok is primed with your session token. Ready to process: <em>{question}</em>"
            }

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
    session['code_verifier'] = flow.code_verifier  # Explicitly preserve the verification code
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(
        get_google_client_config(),
        scopes=SCOPES,
        state=session.get('state'),
        redirect_uri=f"{request.url_root.rstrip('/')}/callback"
    )
    # Complete the handshake protocol using the preserved verification credentials
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
    # Clean up the single-use verification state from memory
    session.pop('code_verifier', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
