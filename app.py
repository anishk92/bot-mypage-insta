import os
from flask import Flask, request
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import base64
import sys

load_dotenv()

# Decode Google credentials from base64 env variable if present
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
media_to_blog_url = {str(record['Instagram Mediaid']): record['Blog URL'] for record in records}

def get_blog_url(media_id):
    return media_to_blog_url.get(str(media_id), "https://techboltx.com")

@app.route("/", methods=["GET"])
def home():
    return "Instagram Comment Auto-Reply Bot is running."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Instagram webhook verification
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json()
        print("📥 Webhook POST data received:", data)
        sys.stdout.flush()

        BOT_USER_ID = '17841402066520501'  # Replace with your Instagram Bot User ID

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})

                if field == "comments":
                    commenter_id = value.get("from", {}).get("id")
                    comment_id = value.get("id")
                    media_id = value.get("media", {}).get("id")

                    print(f"💬 Commenter ID: {commenter_id}, Media ID: {media_id}")
                    sys.stdout.flush()

                    # Skip replying to own comments to avoid infinite loops
                    if commenter_id == BOT_USER_ID:
                        print("Skipping comment from self to avoid loop.")
                        continue

                    if commenter_id and comment_id:
                        reply_text = "Thanks for your comment! DM me to get the blog link. 😊"
                        send_comment_reply(comment_id, reply_text)

                elif field == "messages":
                    sender_id = value.get("sender", {}).get("id")
                    message_text = value.get("message", {}).get("text", "")

                    print(f"📨 DM from {sender_id}: {message_text}")
                    sys.stdout.flush()

                    # Reply with blog link (using first media ID found)
                    if media_to_blog_url:
                        first_media_id = list(media_to_blog_url.keys())[0]
                        blog_url = media_to_blog_url[first_media_id]
                        reply = f"Thanks for messaging! Here's your blog link: {blog_url}"
                        send_dm(sender_id, reply)

        return "ok", 200

def send_dm(recipient_id, message):
    url = f"https://graph.facebook.com/v19.0/{recipient_id}/messages"
    payload = {
        "messaging_type": "RESPONSE",
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "access_token": ACCESS_TOKEN
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
    app.run(debug=True, host='0.0.0.0', port=port)
