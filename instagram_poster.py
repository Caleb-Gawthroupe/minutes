import os
import time
import requests
from dotenv import load_dotenv

def post_photo_to_instagram(access_token, ig_user_id, image_url, caption):
    """
    Posts a photo to an Instagram Business account using the Instagram Graph API.
    
    Args:
        access_token (str): A valid Facebook Graph API Access Token with the necessary permissions.
        ig_user_id (str): The Instagram Business Account ID.
        image_url (str): A public, publicly accessible URL of the image to post.
        caption (str): The text to accompany the photo.
    """
    # Base URL for the Graph API (Using v19.0 as an example, update if needed)
    base_url = "https://graph.facebook.com/v19.0"

    print("Step 1: Creating the media container...")
    media_url = f"{base_url}/{ig_user_id}/media"
    
    # Payload for the media container
    media_payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }

    try:
        response = requests.post(media_url, data=media_payload)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to create media container: {e}")
        if hasattr(e, 'response') and e.response is not None and e.response.text:
            print(f"Error details: {e.response.json()}")
        return

    if 'id' not in result:
        print("Error creating media container:")
        print(result)
        return

    creation_id = result['id']
    print(f"Media container created successfully. Creation ID: {creation_id}")

    # Instagram needs time to process the image before it can be published.
    print("Waiting 5 seconds for Instagram to process the image...")
    time.sleep(5)

    print("Step 2: Publishing the media container...")
    publish_url = f"{base_url}/{ig_user_id}/media_publish"
    
    # Payload to publish the container
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }

    try:
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_response.raise_for_status()
        publish_result = publish_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to publish the photo: {e}")
        if hasattr(e, 'response') and e.response is not None and e.response.text:
            print(f"Error details: {e.response.json()}")
        return

    if 'id' in publish_result:
        print(f"Photo posted successfully! Post ID: {publish_result['id']}")
    else:
        print("Error publishing the photo:")
        print(publish_result)

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # === Configuration ===
    # 1. Credentials are now loaded securely from the .env file
    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID')

    if not ACCESS_TOKEN or not IG_USER_ID:
        print("Error: Missing credentials. Please ensure INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID are set in your .env file.")
        exit(1)
    
    # 2. The URL of your image (MUST be a public URL; local files are not supported directly)
    IMAGE_URL = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSGZdBKcNDO8hu-tnOjXH6X9wYUqNWyMSztzA&s'
    
    # 3. The caption for your post
    CAPTION = 'Hello World! This is an automated post using the Instagram Graph API 🚀'

    # Run the script
    print("Starting Instagram Poster Script...")
    post_photo_to_instagram(ACCESS_TOKEN, IG_USER_ID, IMAGE_URL, CAPTION)
