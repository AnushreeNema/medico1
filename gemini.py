import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables from .env file
load_dotenv()

def gemini_modal_multimodal(image_path):
    # Get API key securely from .env
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = (
        "You are a medical AI. Identify any visible symptoms such as wounds, bruises, bleeding, or swelling "
        "from this image and describe them in detail."
    )

    image = Image.open(image_path)

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt, image])

    return response.text
