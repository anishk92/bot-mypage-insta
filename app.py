import os
from flask import Flask, request
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import base64

load_dotenv()

# Decode google credentials
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
post_to_blog_url = {record['Instagram Shortcode']: record['Blog URL'] for record in records}

def get_blog_url(shortcode):
    return post_to_blog_url.get(shortcode, "https://techboltx.com")

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
        print("Webhook data received:", data)
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "comments":
                    comment_info = change.get("value", {})
                    commenter_id = comment_info.get("from", {}).get("id")
                    post_shortcode = comment_info.get("media_shortcode")
                    if commenter_id and post_shortcode:
                        blog_url = get_blog_url(post_shortcode)
                        message = f"Thanks for commenting! Here's the blog post link: {blog_url}"
                        send_dm(commenter_id, message)
        return "ok", 200

def send_dm(recipient_id, message):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    response = requests.post(url, json=payload)
    print("DM response:", response.status_code, response.text)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
        app.run(host='0.0.0.0', port=port)
