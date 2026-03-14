import os
import requests
import json
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import logging

# Add src to sys.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from ai.agent import CivicAIAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
SMTP_USER = "minutesproject.dev@gmail.com"
SMTP_PASS = os.getenv("SMTP_PASSWORD")
TARGET_EMAIL = "creativearush@gmail.com"

# File paths
HISTORY_FILE = "data/post_history.json"
STATE_FILE = "data/conversation_state.json"
PETITION_FILE = "data/petitions.json"

def send_email(subject, body):
    """Sends an email via SMTP."""
    if not SMTP_PASS:
        logger.error("❌ SMTP_PASSWORD not found in environment.")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"📧 Email sent to {TARGET_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def save_petition(post_uid, name, postal_code):
    """Saves a petition signature to the ledger."""
    os.makedirs("data", exist_ok=True)
    petitions = {}
    if os.path.exists(PETITION_FILE):
        with open(PETITION_FILE, "r") as f:
            petitions = json.load(f)
    
    if post_uid not in petitions:
        petitions[post_uid] = []
    
    petitions[post_uid].append({
        "name": name,
        "postal_code": postal_code,
        "timestamp": json.dumps(True) # Dummy way to get a timestamp placeholder, usually time.time()
    })
    
    with open(PETITION_FILE, "w") as f:
        json.dump(petitions, f, indent=2)
    logger.info(f"✍️ Petition signed for {post_uid} by {name}")

async def process_dm_state(sender_id, sender_username, text, history, state_map):
    """Processes a single DM based on the user's current conversation state."""
    user_state = state_map.get(sender_id, {"state": "INIT"})
    msg_clean = text.strip().upper()
    agent = CivicAIAgent()

    if user_state["state"] == "INIT":
        # Check for UID
        for uid in history.keys():
            if uid in msg_clean:
                state_map[sender_id] = {
                    "state": "AWAIT_ACTION",
                    "post_uid": uid
                }
                logger.info(f"MATCH: {sender_username} started workflow for {uid}")
                print(f"\n[DM] {sender_username} interested in {uid}: {history[uid]['title']}")
                print(f"Action required: Reply with 'EMAIL' or 'PETITION'")
                return

    elif user_state["state"] == "AWAIT_ACTION":
        if "EMAIL" in msg_clean:
            state_map[sender_id]["state"] = "AWAIT_EMAIL_CONTENT"
            print(f"[DM] {sender_username} wants to EMAIL. Awaiting message content...")
        elif "PETITION" in msg_clean:
            state_map[sender_id]["state"] = "AWAIT_PETITION_DATA"
            print(f"[DM] {sender_username} wants to sign PETITION. Awaiting 'Name PostalCode'...")
        else:
            print(f"[DM] {sender_username} sent unknown action. Still awaiting EMAIL/PETITION.")

    elif user_state["state"] == "AWAIT_EMAIL_CONTENT":
        uid = user_state["post_uid"]
        topic = history[uid]["title"]
        print(f"[DM] {sender_username} sent email content. Formatting with AI...")
        
        formatted_email = await agent.format_user_email_async(topic, text)
        if send_email(f"Action Request: {topic}", formatted_email):
            print(f"✅ Email successfully relayed for {sender_username}")
            state_map[sender_id] = {"state": "INIT"} # Reset
        else:
            print(f"❌ Failed to relay email for {sender_username}")

    elif user_state["state"] == "AWAIT_PETITION_DATA":
        uid = user_state["post_uid"]
        # Expect "Name PostalCode"
        parts = text.strip().split(" ", 1)
        if len(parts) >= 1:
            name = parts[0]
            postal = parts[1] if len(parts) > 1 else "Unknown"
            save_petition(uid, name, postal)
            print(f"✅ Petition signed by {sender_username} for {uid}")
            state_map[sender_id] = {"state": "INIT"} # Reset
        else:
            print(f"[DM] {sender_username} sent invalid petition format. Expected 'Name PostalCode'.")

async def run_dm_listener():
    if not PAGE_ACCESS_TOKEN:
        logger.error("❌ Missing FACEBOOK_PAGE_ACCESS_TOKEN in .env")
        return

    # Load Databases
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    
    state_map = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state_map = json.load(f)

    # 1. Get Page ID
    me_url = f"https://graph.facebook.com/v19.0/me?fields=id,instagram_business_account&access_token={PAGE_ACCESS_TOKEN}"
    me_res = requests.get(me_url).json()
    page_id = me_res.get("id")
    if not page_id:
        logger.error(f"❌ Authentication failed: {me_res}")
        return

    # 2. Get Conversations
    conv_url = f"https://graph.facebook.com/v19.0/{page_id}/conversations?platform=instagram&access_token={PAGE_ACCESS_TOKEN}"
    conversations = requests.get(conv_url).json().get("data", [])

    for conv in conversations:
        conv_id = conv["id"]
        msg_url = f"https://graph.facebook.com/v19.0/{conv_id}/messages?fields=message,from,created_time&access_token={PAGE_ACCESS_TOKEN}"
        messages = requests.get(msg_url).json().get("data", [])
        
        # Reverse to process oldest first (chronological)
        for msg in reversed(messages):
            sender_id = msg.get("from", {}).get("id")
            sender_name = msg.get("from", {}).get("username", "Unknown")
            text = msg.get("message", "")
            
            if sender_id and text:
                await process_dm_state(sender_id, sender_name, text, history, state_map)

    # Save State
    os.makedirs("data", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state_map, f, indent=2)
    logger.info("💾 Conversation states updated.")

if __name__ == "__main__":
    asyncio.run(run_dm_listener())