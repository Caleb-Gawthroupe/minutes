import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Using the Page Access Token provided by the user
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

def get_instagram_dms():
    if not PAGE_ACCESS_TOKEN:
        print("❌ Missing FACEBOOK_PAGE_ACCESS_TOKEN in .env")
        return

    # Load post history for matching
    history_file = "data/post_history.json"
    history = {}
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    else:
        print(f"⚠️ Warning: No post history found at {history_file}. Run the pipeline first!")

    # 1. Get the Page ID and IG Account ID
    me_url = "https://graph.facebook.com/v19.0/me"
    me_params = {
        'fields': 'id,name,instagram_business_account',
        'access_token': PAGE_ACCESS_TOKEN
    }
    me_res = requests.get(me_url, params=me_params).json()
    page_id = me_res.get("id")
    ig_account = me_res.get("instagram_business_account", {})
    ig_id = ig_account.get("id")

    if not page_id:
        print("❌ Failed to get Page ID. Check your token:", me_res)
        return
        
    if not ig_id:
        print("❌ Failed to get Instagram Business Account from Page.")
        return

    print(f"✅ Authenticated. Fetching DMs for Page ID: {page_id}")

    # 2. Get all Instagram Conversation Threads
    conv_url = f"https://graph.facebook.com/v19.0/{page_id}/conversations"
    conv_params = {
        "platform": "instagram",
        "access_token": PAGE_ACCESS_TOKEN
    }
    
    response = requests.get(conv_url, params=conv_params).json()
    conversations = response.get("data", [])
    
    if not conversations:
        print("No conversations found.")
        return

    uids = history.keys()
    
    # 3. Loop through threads and check for UID matches
    for conv in conversations:
        conv_id = conv["id"]
        
        msg_url = f"https://graph.facebook.com/v19.0/{conv_id}/messages"
        msg_params = {
            "fields": "message,from,created_time",
            "access_token": PAGE_ACCESS_TOKEN
        }
        
        messages_data = requests.get(msg_url, params=msg_params).json().get("data", [])
        
        # Loop through messages in the thread
        for msg in messages_data:
            sender = msg.get("from", {}).get("username", "Unknown")
            text = msg.get("message", "").strip().upper()
            timestamp = msg.get("created_time", "")
            
            # Check if any UID is mentioned in the DM
            for uid in uids:
                if uid in text:
                    post = history[uid]
                    print("\n" + "🎯 " + "="*40)
                    print(f"MATCH FOUND in DM from {sender}!")
                    print(f"user: said {uid}")
                    print(f"Topic: {post['title']}")
                    print(f"Full Caption:\n{post['caption']}")
                    print(f"Meeting URL: {post['source_url']}")
                    print("="*43 + "\n")
                    break # Found a match in this message

if __name__ == "__main__":
    get_instagram_dms()