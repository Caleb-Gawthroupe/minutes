import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Assuming this is explicitly your Page Access Token
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

def get_instagram_dms():
    if not PAGE_ACCESS_TOKEN:
        print("❌ Missing PAGE_ACCESS_TOKEN in .env")
        return

    # 1. Get the Page ID directly using the Page Access Token
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
        print("Make sure your Instagram Professional account is connected to this Facebook Page.")
        return

    print(f"✅ Authenticated. Fetching DMs for Page ID: {page_id}")

    # 2. Get all Instagram Conversation Threads using the Page ID and platform=instagram
    conv_url = f"https://graph.facebook.com/v19.0/{page_id}/conversations"
    conv_params = {
        "platform": "instagram",
        "access_token": PAGE_ACCESS_TOKEN
    }
    
    response = requests.get(conv_url, params=conv_params).json()
    conversations = response.get("data", [])
    
    if not conversations:
        print("No conversations found. API response:", response)
        print("\n" + "="*60)
        print("❗ CRITICAL STEP REQUIRED IN YOUR INSTAGRAM APP ❗")
        print("Even with all API permissions granted, the API cannot see your")
        print("Direct Messages until you enable it in the Instagram App.")
        print("="*60)
        print("1. Open the Instagram App on your phone.")
        print("2. Go to your Profile -> Menu (top right) -> Settings and privacy.")
        print("3. Scroll down to 'Messages and story replies'.")
        print("4. Tap on 'Message controls'.")
        print("5. Scroll down to 'Connected tools'.")
        print("6. Turn ON 'Allow Access to Messages'.")
        print("="*60 + "\n")
        return

    # 3. Loop through threads and extract the actual messages
    for conv in conversations:
        conv_id = conv["id"]
        
        msg_url = f"https://graph.facebook.com/v19.0/{conv_id}/messages"
        msg_params = {
            "fields": "message,from,created_time",
            "access_token": PAGE_ACCESS_TOKEN
        }
        
        messages_data = requests.get(msg_url, params=msg_params).json().get("data", [])
        
        print(f"\n--- Thread ID: {conv_id} ---")
        
        # Loop through messages in the thread
        for msg in messages_data:
            sender = msg.get("from", {}).get("username", "Unknown")
            text = msg.get("message", "[Attachment/No Text]")
            timestamp = msg.get("created_time", "")
            
            print(f"[{timestamp}] {sender}: {text}")

if __name__ == "__main__":
    get_instagram_dms()