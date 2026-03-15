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
SMTP_USER = os.getenv("CIVIC_EMAIL", "minutesproject.dev@gmail.com")
SMTP_PASS = (os.getenv("EMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD") or "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip().strip('"').strip("'")
TARGET_EMAIL = "creativearush@gmail.com"

# File paths (Legacy - will fallback to Supabase)
HISTORY_FILE = "data/post_history.json"

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
    """Saves a petition signature by communicating directly with Supabase via the Service Key."""
    from supabase import create_client, Client
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY missing. Cannot save petition.")
        return False
        
    supabase: Client = create_client(url, key)
    tag = post_uid.strip()
    
    # 1. Ensure the petition exists
    try:
        # Check if it exists
        existing = supabase.table("petitions").select("tag").eq("tag", tag).execute()
        if not existing.data:
            logger.info(f"Creating new petition topic: {tag}")
            supabase.table("petitions").insert({
                "tag": tag,
                "title": f"Petition regarding {tag}",
                "summary": "Generated automatically via Instagram DM request."
            }).execute()
    except Exception as e:
        logger.error(f"Failed to check/create petition {tag} in Supabase: {e}")
        # Proceed anyway in case it was a race condition creation

    # 2. Add the signature
    try:
        # Prevent duplicates
        formatted_pc = postal_code.replace(" ", "").upper()
        existing_sig = supabase.table("signatures").select("id").eq("petition_tag", tag).ilike("name", name).eq("postal_code", formatted_pc).execute()
        
        if existing_sig.data:
            logger.warning(f"Duplicate signature attempt by {name}")
            return False
            
        res = supabase.table("signatures").insert({
            "petition_tag": tag,
            "name": name,
            "postal_code": formatted_pc
        }).execute()
        
        if res.data:
            logger.info(f"✍️ Petition signed securely for {tag} by {name} via Supabase")
            return True
        else:
            logger.error("❌ Signature rejected by Supabase.")
            return False
    except Exception as e:
        logger.error(f"❌ Supabase Error while signing petition: {e}")
        return False

async def process_dm_state(sender_id, sender_username, text, msg_id, history, supabase, user_state):
    """Processes a single DM based on the user's current conversation state in Supabase."""
    from social.instagram import InstagramClient
    
    # 1. Update bookmark IMMEDIATELY to prevent double-processing if we crash/retry
    user_state["last_msg_id"] = msg_id
    supabase.table("user_states").upsert({
        "sender_id": sender_id,
        "username": sender_username,
        "state_json": user_state,
        "updated_at": "now()"
    }).execute()

    logger.info(f"👤 User {sender_username} (State: {user_state['state']}) -> Processing: {text[:30]}")
    
    msg_clean = text.strip().upper()
    agent = CivicAIAgent()
    ig_client = InstagramClient()

    if user_state["state"] == "INIT":
        # Check for UID
        for uid in history.keys():
            if uid in msg_clean:
                user_state["state"] = "AWAIT_ACTION"
                user_state["post_uid"] = uid
                topic_title = history[uid]['title']
                msg = f"Thanks for your interest in {uid}: {topic_title}!\n\nReply with 'EMAIL' to draft a professional email to the representative, or 'PETITION' to sign the petition."
                logger.info(f"MATCH: {sender_username} started workflow for {uid}")
                ig_client.send_dm_reply(sender_id, msg)
                # No return here! Fall through to save state.

    elif user_state["state"] == "AWAIT_ACTION":
        if "EMAIL" in msg_clean:
            user_state["state"] = "AWAIT_EMAIL_CONTENT"
            msg = "Great! Please send me the raw thoughts you'd like to include in the email. I'll use AI to format it professionally and send it for you."
            ig_client.send_dm_reply(sender_id, msg)
        elif "PETITION" in msg_clean:
            user_state["state"] = "AWAIT_PETITION_DATA"
            msg = "Awesome! To sign the petition securely, please reply with your First Name and Postal Code (e.g., 'John M5V 2H1')."
            ig_client.send_dm_reply(sender_id, msg)
        else:
            msg = "Sorry, I didn't catch that. Please reply with either 'EMAIL' or 'PETITION'."
            ig_client.send_dm_reply(sender_id, msg)

    elif user_state["state"] == "AWAIT_EMAIL_CONTENT":
        uid = user_state["post_uid"]
        topic = history[uid]["title"]
        msg_wait = "Formatting your email with AI... ⏳"
        ig_client.send_dm_reply(sender_id, msg_wait)
        
        formatted_email = await agent.format_user_email_async(topic, text)
        if send_email(f"Action Request: {topic}", formatted_email):
            msg_success = "✅ Your email has been formatted professionally and successfully relayed to the representative!"
            ig_client.send_dm_reply(sender_id, msg_success)
            user_state = {"state": "INIT"} # Reset
        else:
            msg_fail = "❌ Something went wrong while relaying your email. Please try again later."
            ig_client.send_dm_reply(sender_id, msg_fail)

    elif user_state["state"] == "AWAIT_PETITION_DATA":
        uid = user_state["post_uid"]
        # Expect "Name PostalCode"
        parts = text.strip().split(" ", 1)
        if len(parts) >= 1:
            name = parts[0]
            postal = parts[1] if len(parts) > 1 else "Unknown"
            if save_petition(uid, name, postal):
                msg_success = f"✅ Thank you, {name}! Your signature for {uid} has been securely recorded."
                ig_client.send_dm_reply(sender_id, msg_success)
                user_state = {"state": "INIT"} # Reset
            else:
                msg_fail = "❌ Failed to secure your signature. Make sure your Postal Code is a valid format (e.g., M5V 2H1) and you haven't already signed."
                ig_client.send_dm_reply(sender_id, msg_fail)
        else:
            msg_retry = "Invalid format. Please reply with exactly: 'Name PostalCode'."
            ig_client.send_dm_reply(sender_id, msg_retry)
            
    # Final save to ensure state transitions (like AWAIT -> INIT) are persisted
    supabase.table("user_states").upsert({
        "sender_id": sender_id,
        "username": sender_username,
        "state_json": user_state,
        "updated_at": "now()"
    }).execute()

async def run_dm_listener():
    from supabase import create_client, Client
    import socket
    from urllib.parse import urlparse
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY missing.")
        return
        
    # --- CONNECTIVITY DIAGNOSTIC ---
    try:
        parsed = urlparse(SUPABASE_URL)
        hostname = parsed.hostname
        logger.info(f"🔍 Diagnostic: Testing connection to {hostname}...")
        
        # 1. DNS Check
        try:
            ip = socket.gethostbyname(hostname)
            logger.info(f"✅ DNS Resolved: {hostname} -> {ip}")
        except socket.gaierror:
            logger.error(f"❌ DNS Error: Could not resolve '{hostname}'. Your SUPABASE_URL might be wrong.")
            return

        # 2. Basic Reachability
        res = requests.get(SUPABASE_URL, timeout=10)
        logger.info(f"✅ HTTP Reachability: {SUPABASE_URL} returned {res.status_code}")
        
    except Exception as e:
        logger.warning(f"⚠️ Diagnostic Warning: Basic connectivity test failed: {e}")
    # ------------------------------

    logger.info(f"Connecting to Supabase at {SUPABASE_URL[:15]}...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if not PAGE_ACCESS_TOKEN:
        logger.error("❌ Missing FACEBOOK_PAGE_ACCESS_TOKEN in .env")
        return

    # 1. Load Post History from Supabase
    history = {}
    try:
        posts_res = supabase.table("posts").select("*").execute()
        for p in posts_res.data:
            history[p["uid"]] = p
        logger.info(f"Loaded {len(history)} items from Supabase post history.")
    except Exception as e:
        logger.error(f"Failed to load post history from Supabase: {e}")

    # 2. Get IDs
    me_url = f"https://graph.facebook.com/v19.0/me?fields=id,instagram_business_account&access_token={PAGE_ACCESS_TOKEN}"
    me_res = requests.get(me_url).json()
    page_id = me_res.get("id")
    insta_id = me_res.get("instagram_business_account", {}).get("id")
    
    if not page_id:
        logger.error(f"❌ Authentication failed: {me_res}")
        return

    # 3. Get Conversations
    conv_url = f"https://graph.facebook.com/v19.0/{page_id}/conversations?platform=instagram&access_token={PAGE_ACCESS_TOKEN}"
    conversations = requests.get(conv_url).json().get("data", [])

    for conv in conversations:
        conv_id = conv["id"]
        msg_url = f"https://graph.facebook.com/v19.0/{conv_id}/messages?fields=message,from,created_time,id&access_token={PAGE_ACCESS_TOKEN}"
        resp = requests.get(msg_url).json()
        messages = resp.get("data", [])
        
        if not messages:
            continue

        # 4. Get User Info from the newest message (most likely to have it)
        sample_msg = messages[0]
        sender_id = sample_msg.get("from", {}).get("id")
        sender_name = sample_msg.get("from", {}).get("username", "Unknown")
        
        # Skip if conversation is with the Page/Bot itself
        is_self = (sender_id == page_id or (insta_id and sender_id == insta_id))
        if is_self: continue

        # 5. Fetch Bookmark from Supabase
        state_res = supabase.table("user_states").select("state_json").eq("sender_id", sender_id).execute()
        user_state = state_res.data[0]["state_json"] if state_res.data else {"state": "INIT", "last_msg_id": None}
        last_id = user_state.get("last_msg_id")

        # 6. Find New Messages
        new_messages = []
        found_bookmark = False
        if last_id:
            for m in messages:
                if m.get("id") == last_id:
                    found_bookmark = True
                    break
                new_messages.append(m)
            
            if not found_bookmark:
                # The bookmark fell off the list OR hasn't been set.
                # To be safe, we only process the absolute latest message.
                logger.info(f"⚠️ Bookmark {last_id} NOT found for {sender_name} in recent history. Jumping to present (processing only latest msg).")
                new_messages = [messages[0]]
        else:
            # BRAND NEW USER: Just process the latest message.
            logger.info(f"🆕 New user detected: {sender_name}. Processing only latest message.")
            new_messages = [messages[0]]
        
        # 7. Process in Order (Oldest First)
        if new_messages:
            count = len(new_messages)
            if count > 1:
                logger.info(f"📥 Found {count} new message(s) from {sender_name}")
            
            for m in reversed(new_messages):
                text = m.get("message", "")
                msg_id = m.get("id")
                created_at = m.get("created_time")
                
                if not text: continue
                
                # Double-check sender (some convs are group!)
                m_sender_id = m.get("from", {}).get("id")
                if m_sender_id != sender_id: continue

                # Freshness Check: Skip if message is older than 30 minutes
                # This prevents "re-processing" loops if everything else fails
                from datetime import datetime, timezone, timedelta
                try:
                    clean_time = created_at.replace("+0000", "+00:00")
                    msg_time = datetime.fromisoformat(clean_time)
                    if datetime.now(timezone.utc) - msg_time > timedelta(minutes=30):
                        continue
                except Exception:
                    pass

                await process_dm_state(sender_id, sender_name, text, msg_id, history, supabase, user_state)

    logger.info("🏁 DM processing complete.")

if __name__ == "__main__":
    asyncio.run(run_dm_listener())