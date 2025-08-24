from flask import Flask, render_template, request, jsonify, session
import os
import subprocess
import webbrowser
import pyttsx3
import google.generativeai as genai
import uuid
import platform
import threading
import re

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in production

# ---------- Speech Engine ----------
engine = pyttsx3.init()
last_reply = ""  # Stores last bot reply

def speak_text(text):
    """Speak text safely in a separate thread to avoid run loop errors."""
    if not text:
        return
    def run_speech():
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=run_speech, daemon=True).start()

# ---------- Gemini AI ----------
# Put your key in an environment variable if possible:
#   setx GEMINI_API_KEY "YOUR_KEY"  (Windows)
#   export GEMINI_API_KEY=YOUR_KEY  (macOS/Linux)
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBYesGjVe5oinLRiY_3ndW50KFBgiNjrvo")
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception:
    model = None  # Still allow the app to run without AI

# Store chat sessions per user
chat_sessions = {}

# Popular sites (server-side fallback too)
POPULAR_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://www.twitter.com",
    "whatsapp": "https://web.whatsapp.com",
    "insta": "https://www.instagram.com",
    "instagram": "https://www.instagram.com",
}

PUNCTUATION_STRIP = re.compile(r"[.,!?;:]+$")

def normalize_target(text: str) -> str:
    """lowercase, trim, and strip trailing punctuation like '.', ',', '!'."""
    if not text:
        return ""
    return PUNCTUATION_STRIP.sub("", text.strip().lower())

# ---------- Open Apps ----------
def open_app(app_name):
    """
    Try to open a desktop app by name. On Windows, known apps handled explicitly.
    For unknown names, attempt to run directly; if that fails, return a helpful error.
    """
    app_name = normalize_target(app_name)
    system = platform.system()

    try:
        # If it's a known website key, open that
        if app_name in POPULAR_SITES:
            webbrowser.open_new_tab(POPULAR_SITES[app_name])
            return f"🌐 Opening {app_name}…"

        # If it looks like a URL, open it
        if app_name.startswith(("http://", "https://")):
            webbrowser.open_new_tab(app_name)
            return f"🌐 Opening website {app_name}"

        if system == "Windows":
            # Known Windows apps
            if app_name in ("notepad",):
                os.startfile("notepad.exe")
                return "✅ Opening Notepad…"
            if app_name in ("calculator", "calc"):
                os.startfile("calc.exe")
                return "✅ Opening Calculator…"
            if app_name == "chrome":
                # Try default location; fallback to 'start' if not found
                chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                if os.path.exists(chrome_path):
                    subprocess.Popen([chrome_path])
                else:
                    subprocess.Popen(["start", "", "chrome"], shell=True)
                return "✅ Opening Chrome…"

            # Try to start by name (PATH)
            try:
                subprocess.Popen([app_name], shell=True)
                return f"✅ Opening {app_name}…"
            except FileNotFoundError:
                # Try Windows start (can open apps on PATH)
                subprocess.Popen(["start", "", app_name], shell=True)
                return f"✅ Opening {app_name}…"

        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
            return f"✅ Opening {app_name}…"

        else:  # Linux / others
            subprocess.Popen([app_name])
            return f"✅ Opening {app_name}…"

    except FileNotFoundError:
        return f"❌ Could not find '{app_name}'"
    except Exception as e:
        return f"⚠️ Error opening '{app_name}': {str(e)}"

# ---------- AI + Command Handler ----------
def nova_response(user_input, user_id):
    global last_reply

    # Get or create session
    chat = chat_sessions.get(user_id)
    if not chat and model:
        chat = model.start_chat()
        chat_sessions[user_id] = chat

    raw_text = user_input or ""
    ui = normalize_target(raw_text)

    # --- Open apps or websites ---
    if ui.startswith("open "):
        target_raw = raw_text[5:]  # keep original for nicer echo
        target = normalize_target(target_raw)

        # websites by key
        if target in POPULAR_SITES:
            webbrowser.open_new_tab(POPULAR_SITES[target])
            reply = f"🌐 Opening {target}…"
            last_reply = reply
            speak_text(reply)
            return reply

        # direct url?
        if target_raw.strip().lower().startswith(("http://", "https://")):
            url = target_raw.strip()
            webbrowser.open_new_tab(url)
            reply = f"🌐 Opening website {url}"
            last_reply = reply
            speak_text(reply)
            return reply

        # otherwise treat as app name
        reply = open_app(target)
        last_reply = reply
        speak_text(reply)
        return reply

    # --- Read aloud last reply ---
    if ui == "read":
        if last_reply:
            speak_text(last_reply)
            return f"🔊 Reading aloud: {last_reply}"
        return "❌ No previous reply to read aloud."

    # --- Personalization ---
    if "my name is " in ui:
        name = raw_text.split("my name is ", 1)[-1].strip()
        name = PUNCTUATION_STRIP.sub("", name)
        session['username'] = name
        reply = f"Nice to meet you, {name}!"
        last_reply = reply
        speak_text(reply)
        return reply

    # --- AI response ---
    try:
        if not model:
            reply = "🤖 AI model not configured. Please set GEMINI_API_KEY."
        else:
            chat = chat_sessions.get(user_id)
            if not chat:
                chat = model.start_chat()
                chat_sessions[user_id] = chat
            response = chat.send_message(raw_text)
            reply = (response.text or "").strip() or "🤖 (No response)"
        last_reply = reply
        return reply
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ---------- Flask Routes ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True) or {}
    message = data.get("message", "")

    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id

    reply = nova_response(message, user_id)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    # host='0.0.0.0' if you need LAN access
    app.run(debug=True)
