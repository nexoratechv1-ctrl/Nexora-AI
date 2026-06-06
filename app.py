import os
import requests
import json
import random
import hashlib
import sqlite3
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nexora_secret_key_2025')
CORS(app)

# ========== GROQ API ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ========== DATABASE SETUP ==========
DB_NAME = "nexora_users.db"

def init_user_db():
    """Initialize user database with tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Conversations table (memory ya mazungumzo)
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  role TEXT,
                  message TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Personality results table
    c.execute('''CREATE TABLE IF NOT EXISTS personality
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  animal TEXT,
                  trait TEXT,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Game stats table
    c.execute('''CREATE TABLE IF NOT EXISTS game_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  wins INTEGER DEFAULT 0,
                  total_attempts INTEGER DEFAULT 0,
                  last_played TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_user_db()

# ========== HELPER FUNCTIONS ==========
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_id(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def create_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                  (username, hash_password(password)))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
              (username, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_conversation(user_id, role, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, role, message) VALUES (?, ?, ?)",
              (user_id, role, message))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, limit=20):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, message FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
              (user_id, limit))
    results = c.fetchall()
    conn.close()
    # Return in chronological order
    history = []
    for role, msg in reversed(results):
        history.append(f"{role}: {msg}")
    return "\n".join(history)

def save_personality(user_id, animal, trait):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO personality (user_id, animal, trait) VALUES (?, ?, ?)",
              (user_id, animal, trait))
    conn.commit()
    conn.close()

def get_personality(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT animal, trait FROM personality WHERE user_id = ? ORDER BY date DESC LIMIT 1",
              (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else None

def update_game_stats(user_id, won, attempts):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT wins, total_attempts FROM game_stats WHERE user_id = ?", (user_id,))
    existing = c.fetchone()
    
    if existing:
        wins = existing[0] + (1 if won else 0)
        total_attempts = existing[1] + attempts
        c.execute("UPDATE game_stats SET wins = ?, total_attempts = ?, last_played = CURRENT_TIMESTAMP WHERE user_id = ?",
                  (wins, total_attempts, user_id))
    else:
        c.execute("INSERT INTO game_stats (user_id, wins, total_attempts, last_played) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                  (user_id, 1 if won else 0, attempts))
    conn.commit()
    conn.close()

def get_game_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT wins, total_attempts FROM game_stats WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (0, 0)

# ========== LOGIN DECORATOR ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ========== FEATURE FUNCTIONS ==========
def generate_image(prompt):
    try:
        clean_prompt = prompt.replace("chora", "").replace("picha ya", "").replace("draw", "").strip()
        encoded_prompt = requests.utils.quote(clean_prompt)
        return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
    except:
        return None

def ask_groq(question, user_name, history):
    if not GROQ_API_KEY:
        return get_fallback_response(question, user_name)
    
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        system_prompt = f"""Wewe ni Nexora AI. Jina lako ni NEXORA AI. Ulitengenezwa na DENIS ALBERT, mwanafunzi wa ST. AMEDEUS.
Jina la mtumiaji ni {user_name}. Jibu kwa KISWAHILI tu. Tumia emoji kidogo.
Mazungumzo yaliyopita: {history}"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
            "temperature": 0.7,
            "max_tokens": 400
        }
        
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "Samahani, sikuelewa.")
        else:
            return get_fallback_response(question, user_name)
    except:
        return get_fallback_response(question, user_name)

def get_fallback_response(question, user_name):
    q = question.lower()
    if "jina lako" in q or "unaitwa nani" in q:
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert, mwanafunzi wa St. Amedeus. 🎓😊"
    if "habari" in q:
        return f"Habari yangu ni nzuri sana, {user_name}! 😊"
    return f"Samahani, {user_name}. Sijaelewa vizuri. Jaribu tena! 😊"

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chat.html')
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Tafadhali jaza nafasi zote"})
    
    user_id = authenticate_user(username, password)
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"success": False, "error": "Jina la mtumiaji au password si sahihi"})

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Tafadhali jaza nafasi zote"})
    
    if len(password) < 4:
        return jsonify({"success": False, "error": "Password lazima iwe na herufi 4 au zaidi"})
    
    user_id = create_user(username, password)
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"success": False, "error": "Jina la mtumiaji tayari lipo"})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    msg = data.get('message', '')
    user_id = session['user_id']
    username = session['username']
    
    q = msg.lower().strip()
    
    # Save user message
    save_conversation(user_id, "Mtumiaji", msg)
    
    # Get conversation history
    history = get_conversation_history(user_id, 10)
    
    # Get response
    reply = ask_groq(msg, username, history)
    
    # Save AI response
    save_conversation(user_id, "Nexora", reply)
    
    return jsonify({"reply": reply})

@app.route('/api/profile', methods=['GET'])
@login_required
def profile():
    user_id = session['user_id']
    personality = get_personality(user_id)
    wins, attempts = get_game_stats(user_id)
    
    return jsonify({
        "username": session['username'],
        "personality": personality,
        "wins": wins,
        "total_attempts": attempts
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
