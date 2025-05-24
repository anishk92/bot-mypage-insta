import os
import sys
import base64
import requests
import gspread
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Decode Google credentials from base64
if os.getenv("GOOGLE_CREDENTIALS_B64"):
    with open("google-credentials.json", "wb") as f:
        f.write(base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_B64")))

# Flask app
app = Flask(__name__)

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
BOT_USER_ID = os.getenv("IG_BOT_USER_ID", "")  # Set this in your .env if not hardcoded

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("blogurl").sheet1
records = sheet.get_all_records()
media_to_blog_url = {str(record['Instagram Mediaid']): record['Blog URL'] for record in records}

def get_blog_url(media_id):
    return media_to_blog_url.get(str(media_id), "https://techboltx.com")

@app.route("/", methods=["GET"])
def home():
    return "Instagram Comment + DM Auto-Reply Bot is running."

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
            # 🔁 Handle comment replies from IG Graph API
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})

                if field == "comments":
                    commenter_id = value.get("from", {}).get("id")
                    comment_id = value.get("id")
                    media_id = value.get("media", {}).get("id")

                    print(f"💬 Comment from {commenter_id} on media {media_id}")
                    sys.stdout.flush()

                    if commenter_id == BOT_USER_ID:
                        print("⏭️ Skipping self-comment to avoid loop.")
                        continue

                    reply_text = "Thanks for your comment! DM me to get the blog link. 😊"
                    send_comment_reply(comment_id, reply_text)

            # 💬 Handle DMs via Messenger webhook format
            for message_event in entry.get("messaging", []):
                sender_id = message_event.get("sender", {}).get("id")
                message_text = message_event.get("message", {}).get("text", "")

                print(f"📨 DM received from {sender_id}: {message_text}")
                sys.stdout.flush()

                if sender_id and message_text:
                    # Always send the first blog link for now
                    if media_to_blog_url:
                        first_media_id = list(media_to_blog_url.keys())[0]
                        blog_url = media_to_blog_url[first_media_id]
                    else:
                        blog_url = "https://techboltx.com"

                    reply = f"Thanks for messaging! Here's your blog link: {blog_url}"
                    send_dm(sender_id, reply)

        return "ok", 200

def send_dm(recipient_id, message):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "messaging_type": "RESPONSE",
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    response = requests.post(url, json=payload)
    print("📤 DM response:", response.status_code, response.text)
    sys.stdout.flush()

def send_comment_reply(comment_id, text):
    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
    payload = {
        "message": text,
        "access_token": ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    print("💬 Comment reply response:", response.status_code, response.text)
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
