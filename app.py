import os
from flask import Flask, request
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import base64
import sys

load_dotenv()

# Decode Google service credentials
if os.getenv("GOOGLE_CREDENTIALS_B64"):
    with open("google-credentials.json", "wb") as f:
        f.write(base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_B64")))

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("blogurl").sheet1
records = sheet.get_all_records()
mediaid_to_blog_url = {str(record['Instagram Mediaid']): record['Blog URL'] for record in records}

def get_blog_url(media_id):
    return mediaid_to_blog_url.get(str(media_id), "https://techboltx.com")

@app.route("/", methods=["GET"])
def home():
    return "Instagram Comment to Blog URL DM Bot is running."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json()
        print("📥 Webhook POST data received:", data)
        sys.stdout.flush()

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "comments":
                    value = change.get("value", {})
                    commenter_id = value.get("from", {}).get("id")
                    media_id = value.get("media", {}).get("id")

                    print(f"💬 Commenter ID: {commenter_id}, Media ID: {media_id}")
                    sys.stdout.flush()

                    if commenter_id and media_id:
                        blog_url = get_blog_url(media_id)
                        message = f"Thanks for commenting! Here’s the blog post: {blog_url}"
                        send_dm(commenter_id, message)

        return "ok", 200

def send_dm(recipient_id, message):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    response = requests.post(url, json=payload)
    print(f"📤 DM response: {response.status_code} {response.text}")
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
