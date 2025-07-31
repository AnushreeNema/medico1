import os
from groq import Groq

# --- Step 2: Classify severity with Groq ---
def groq(user_input1):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"Classify this emergency input as 'mild', 'moderate', or 'severe': {user_input1}",
            }
        ],
        model="llama3-70b-8192",
        stream=False,
    )
    return chat_completion.choices[0].message.content.strip()