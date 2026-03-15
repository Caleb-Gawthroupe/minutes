import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip().strip('"').strip("'")

def reset_all_states():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials missing in .env")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    confirm = input("Are you sure you want to CLEAR all user conversation states? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        # Delete all rows in user_states
        res = supabase.table("user_states").delete().neq("sender_id", "0").execute()
        print(f"✅ Successfully cleared {len(res.data) if res.data else 0} user states.")
        print("The next time you message the bot, it will start from fresh INIT state.")
    except Exception as e:
        print(f"❌ Failed to clear states: {e}")

if __name__ == "__main__":
    reset_all_states()
