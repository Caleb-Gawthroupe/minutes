import os
import requests
from dotenv import load_dotenv

load_dotenv()

PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")  # FB Page ID — Instagram messaging routes through this


def send_instagram_dm(recipient_id, message_text):
    """
    Sends an Instagram Direct Message using the Facebook Graph API.

    Args:
        recipient_id (str): The Instagram-Scoped ID (IGSID) of the recipient.
        message_text (str): The text message to send.
    """
    if not PAGE_ACCESS_TOKEN:
        print("❌ Missing PAGE_ACCESS_TOKEN in .env")
        return False

    if not FACEBOOK_PAGE_ID:
        print("❌ Missing FACEBOOK_PAGE_ID in .env")
        return False

    try:
        # Instagram messaging routes through the Facebook Page ID, not the IG account ID
        url = f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}/messages"

        payload = {
            "messaging_type": "RESPONSE",
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text
            }
        }

        params = {
            "access_token": PAGE_ACCESS_TOKEN
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, params=params, headers=headers, json=payload)
        response_data = response.json()

        if response.status_code == 200 and ("message_id" in response_data or "recipient_id" in response_data):
            print(f"✅ Successfully sent message to {recipient_id}!")
            print(f"Message ID: {response_data['message_id']}")
            return True
        else:
            print(f"❌ Failed to send message. Status: {response.status_code}")
            print("API Response:", response_data)

            error = response_data.get("error", {})
            error_code = error.get("code")

            if error_code == 10:
                print("\n💡 Permission error: The user must have messaged you first (24hr window for Standard Access).")
            elif error_code == 3:
                print("\n💡 OAuth error: In Development Mode you can only message users who are app testers.")
                print("   → Meta Developer Dashboard → App Roles → Roles → Add Instagram Tester")
                print("   → They must accept via Instagram Settings → Apps and Websites → Tester Invites")
            elif error_code == 100:
                print("\n💡 Invalid parameter — double-check the recipient IGSID is correct.")

            return False

    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False


if __name__ == "__main__":
    send_instagram_dm("3773426829460674", "TEST TEST API IS FIXED!")