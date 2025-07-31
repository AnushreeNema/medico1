import os
import sqlite3
from uuid import uuid4
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import anthropic
import openai
import google.generativeai as genai
from dotenv import load_dotenv

from rag_module import retrieve_context as rag1
from gemini import gemini_modal_multimodal
from Groq import groq

# Load keys
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# FastAPI app
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_html():
    return FileResponse("static/emergency_assistant.html")

# Database setup
DB_PATH = "conversations.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        filename TEXT,
        analysis TEXT
    )
""")
conn.commit()

# Session
SESSION_ID = str(uuid4())
severity_checked = False

# -------- Gemini helper for detecting image request --------
def gemini_requests_image(reply_text):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You're an AI that detects if the assistant's message is asking for an image. "
            "Respond ONLY with 'yes' or 'no'.\n\n"
            f"Assistant says: {reply_text}"
        )
        result = model.generate_content(prompt)
        return result.text.strip().lower().startswith("yes")
    except Exception as e:
        print(f"[Gemini detection failed]: {e}")
        return False

# -------- Emergency assistant logic --------
def claude1_agent_emergency(user_input, extra_info=None):
    rag_context = rag1(user_input)
    prompt = (
        f"You are a helpful assistant in emergency medical situations or non emergency situations. "
        f"Respond concisely, guide step-by-step, and ask for images if needed. And please guide one step at a time and provide nice solutions.\n"
        f"User input: {user_input}\nContext: {rag_context}\n"
    )
    if extra_info:
        prompt += f"Image observations: {extra_info}\n"

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    reply = "".join([block.text if hasattr(block, 'text') else str(block) for block in message.content])
    request_image = gemini_requests_image(reply)

    # Store in DB
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (SESSION_ID, "user", user_input))
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (SESSION_ID, "assistant", reply))
    conn.commit()

    return {
        "reply": reply,
        "request_image": request_image
    }

# -------- Routes --------
@app.post("/chat")
async def chat(request: Request):
    global severity_checked
    data = await request.json()
    user_input = data.get("message")

    # First message: get severity but still continue response
    if not severity_checked:
        severity_level = groq(user_input)
        severity_checked = True  # Don't return early

    result = claude1_agent_emergency(user_input)
    return JSONResponse(content=result)

@app.post("/analyze-image")
async def analyze_image(image: UploadFile = File(...)):
    image_path = f"temp_{uuid4().hex}.jpg"
    with open(image_path, "wb") as f:
        f.write(await image.read())

    try:
        gemini_result = gemini_modal_multimodal(image_path)
        response = claude1_agent_emergency("Analyze this injury image.", extra_info=gemini_result)

        # Store image metadata
        cursor.execute("INSERT INTO images (session_id, filename, analysis) VALUES (?, ?, ?)",
                       (SESSION_ID, image_path, gemini_result))
        conn.commit()

        return JSONResponse(content={"result": response["reply"], "request_image": False})

    except Exception as e:
        return JSONResponse(status_code=500, content={"result": f"Image analysis failed: {str(e)}"})

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    temp_path = f"temp_{uuid4().hex}.webm"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    try:
        with open(temp_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)["text"]
        result = claude1_agent_emergency(transcript)

        return JSONResponse(content={
            "transcript": transcript,
            "reply": result["reply"],
            "request_image": result["request_image"]
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f" Audio transcription failed: {str(e)}"})

# -------- Run Server --------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
