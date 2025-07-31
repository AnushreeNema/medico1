# vapi_utils.py
import requests
import os

VAPI_API_KEY = os.getenv("VAPI_API_KEY")

def send_tts_to_vapi(text, user_id="user-123"):
    url = "https://api.vapi.ai/message/send"
    
    payload = {
        "user": {"id": user_id},
        "message": {
            "type": "text",
            "text": text
        }
    }

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print("Error sending TTS to Vapi:", e)
        return None
