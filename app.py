import os
import requests
import json
import random
import hashlib
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, send_from_directory, redirect
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nexora_secret_key_2025_talent_day')
CORS(app)

# ========== GROQ API ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ========== DATABASE SETUP ==========
DB_NAME = "nexora_users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS personality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal TEXT NOT NULL,
        trait TEXT NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS game_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        wins INTEGER DEFAULT 0,
        total_attempts INTEGER DEFAULT 0,
        current_game_number INTEGER,
        current_game_attempts INTEGER DEFAULT 0,
        game_active INTEGER DEFAULT 0,
        last_played TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # ========== JEDWALI LA ANALYTICS ==========
    c.execute('''CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        session_id TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        user_agent TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ========== HELPER FUNCTIONS ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
    history = []
    for role, msg in reversed(results):
        history.append(f"{role}: {msg}")
    return "\n".join(history)

def save_personality(user_id, animal, trait):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM personality WHERE user_id = ?", (user_id,))
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

def get_game_state(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT wins, total_attempts, current_game_number, current_game_attempts, game_active FROM game_stats WHERE user_id = ?",
              (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"wins": result[0], "total_attempts": result[1], 
                "number": result[2], "attempts": result[3], "active": result[4]}
    return {"wins": 0, "total_attempts": 0, "number": None, "attempts": 0, "active": False}

def update_game_state(user_id, wins=None, total_attempts=None, number=None, attempts=None, active=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM game_stats WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    
    if exists:
        updates = []
        values = []
        if wins is not None:
            updates.append("wins = ?")
            values.append(wins)
        if total_attempts is not None:
            updates.append("total_attempts = ?")
            values.append(total_attempts)
        if number is not None:
            updates.append("current_game_number = ?")
            values.append(number)
        if attempts is not None:
            updates.append("current_game_attempts = ?")
            values.append(attempts)
        if active is not None:
            updates.append("game_active = ?")
            values.append(active)
        updates.append("last_played = CURRENT_TIMESTAMP")
        
        if updates:
            values.append(user_id)
            c.execute(f"UPDATE game_stats SET {', '.join(updates)} WHERE user_id = ?", values)
    else:
        c.execute("""INSERT INTO game_stats (user_id, wins, total_attempts, current_game_number, current_game_attempts, game_active, last_played) 
                     VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                  (user_id, wins or 0, total_attempts or 0, number, attempts or 0, 1 if active else 0))
    
    conn.commit()
    conn.close()

# ========== ANALYTICS FUNCTIONS ==========
def track_user_action(user_id, session_id, action, details=None):
    """Rekodi kitendo cha mtumiaji"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO analytics (user_id, session_id, action, details) 
                 VALUES (?, ?, ?, ?)""", 
              (user_id, session_id, action, details))
    conn.commit()
    conn.close()

def get_user_stats():
    """Pata takwimu za watumiaji"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE created_at > date('now', '-7 days')")
    new_users_week = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
    new_users_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM conversations")
    total_conversations = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM conversations WHERE date(timestamp) = date('now')")
    conversations_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT session_id) FROM analytics WHERE date(timestamp) = date('now')")
    active_sessions_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM personality")
    personality_count = c.fetchone()[0]
    
    c.execute("""SELECT a.timestamp, u.username, a.action, a.details 
                 FROM analytics a 
                 LEFT JOIN users u ON a.user_id = u.id 
                 ORDER BY a.timestamp DESC LIMIT 20""")
    recent_activity = c.fetchall()
    
    conn.close()
    
    return {
        "total_users": total_users,
        "new_users_week": new_users_week,
        "new_users_today": new_users_today,
        "total_conversations": total_conversations,
        "conversations_today": conversations_today,
        "active_sessions_today": active_sessions_today,
        "personality_count": personality_count,
        "recent_activity": recent_activity
    }

# ========== FEATURE FUNCTIONS ==========
def generate_image(prompt):
    try:
        clean_prompt = prompt.replace("chora", "").replace("picha ya", "").replace("draw", "").strip()
        encoded_prompt = requests.utils.quote(clean_prompt)
        return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
    except:
        return None

def personality_test_result(answers):
    likes_night = answers.get('likes_night', False)
    likes_flying = answers.get('likes_flying', False)
    likes_people = answers.get('likes_people', False)
    
    if likes_night and likes_flying:
        return {"animal": "Bundi 🦉", "trait": "Una hekima na utulivu. Wewe ni mwenye busara!"}
    elif likes_night and not likes_flying:
        return {"animal": "Paka 🐱", "trait": "Wewe ni mwenye ustaarabu, mpenda faragha, na unajitegemea!"}
    elif not likes_night and likes_flying:
        return {"animal": "Ndege 🦅", "trait": "Una roho ya uhuru, unapenda kusafiri na kuchunguza mambo mapya!"}
    elif not likes_night and likes_people:
        return {"animal": "Simba 🦁", "trait": "Una uongozi, ujasiri, na unapenda kuwa katikati ya watu!"}
    else:
        return {"animal": "Tembo 🐘", "trait": "Una hekima, uaminifu, na unakumbuka mambo mengi!"}

def ask_groq(question, user_name, history):
    if not GROQ_API_KEY:
        return get_fallback_response(question, user_name)
    
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        system_prompt = f"""Wewe ni Nexora AI. Jina lako ni NEXORA AI. 
Ulitengenezwa na DENIS ALBERT, mwanafunzi wa ST. AMEDEUS.
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

# ========== SERVE STATIC FILES ==========
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

# ========== GENERATE ICON "N" USING SVG ==========
@app.route('/static/icon-512.png')
def generate_icon():
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
        <rect width="512" height="512" fill="#a855f7" rx="100"/>
        <text x="256" y="380" font-family="Arial, Helvetica, sans-serif" font-size="380" font-weight="bold" fill="white" text-anchor="middle">N</text>
    </svg>'''
    return svg_content, 200, {'Content-Type': 'image/svg+xml'}

# ========== DASHBOARD YA TAKWIMU ==========
@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session:
        return redirect('/')
    
    stats = get_user_stats()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nexora AI - Takwimu za Watumiaji</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, 'Segoe UI', sans-serif;
                background: #0f0f13;
                color: #e4e4e7;
                padding: 20px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: #c084fc; margin-bottom: 20px; }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #1a1a24;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #2a2a3a;
                text-align: center;
            }}
            .stat-number {{
                font-size: 2.5rem;
                font-weight: bold;
                color: #a855f7;
            }}
            .stat-label {{
                color: #a1a1aa;
                margin-top: 8px;
            }}
            .activity-table {{
                width: 100%;
                background: #1a1a24;
                border-radius: 16px;
                overflow: auto;
                border: 1px solid #2a2a3a;
            }}
            .activity-table th, .activity-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #2a2a3a;
            }}
            .activity-table th {{
                background: #2a2a3a;
                color: #c084fc;
            }}
            .back-btn {{
                background: #a855f7;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                cursor: pointer;
                margin-bottom: 20px;
            }}
            .back-btn:hover {{ background: #7c3aed; }}
        </style>
    </head>
    <body>
        <div class="container">
            <button class="back-btn" onclick="window.location.href='/'">← Nyuma kwa Chat</button>
            <h1>📊 Takwimu za Watumiaji - Nexora AI</h1>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{stats['total_users']}</div>
                    <div class="stat-label">Jumla ya Watumiaji</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['new_users_week']}</div>
                    <div class="stat-label">Wapya Wiki Hii</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['new_users_today']}</div>
                    <div class="stat-label">Wapya Leo</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['active_sessions_today']}</div>
                    <div class="stat-label">Vikao Hai Leo</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['total_conversations']}</div>
                    <div class="stat-label">Jumla ya Mazungumzo</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['conversations_today']}</div>
                    <div class="stat-label">Mazungumzo Leo</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['personality_count']}</div>
                    <div class="stat-label">Waliopima Personality</div>
                </div>
            </div>
            
            <h2>📝 Shughuli za Hivi Karibuni</h2>
            <div style="overflow-x: auto;">
                <table class="activity-table">
                    <thead>
                        <tr><th>Muda</th><th>Mtumiaji</th><th>Kitendo</th><th>Maelezo</th></tr>
                    </thead>
                    <tbody>
    """
    
    for activity in stats['recent_activity']:
        timestamp = activity[0]
        username = activity[1] if activity[1] else "Anonymous"
        action = activity[2]
        details = activity[3][:50] if activity[3] else "-"
        html += f"<tr><td>{timestamp}</td><td>{username}</td><td>{action}</td><td>{details}</td></tr>"
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chat.html', username=session['username'])
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
        # Tengeneza session_id kwa ajili ya tracking
        session['session_id'] = str(uuid.uuid4())
        track_user_action(user_id, session['session_id'], 'login', f"Mtumiaji {username} aliingia")
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"success": False, "error": "Jina au password si sahihi"})

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
        session['session_id'] = str(uuid.uuid4())
        track_user_action(user_id, session['session_id'], 'signup', f"Mtumiaji {username} alijisajili")
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"success": False, "error": "Jina la mtumiaji tayari lipo"})

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session and 'session_id' in session:
        track_user_action(session['user_id'], session['session_id'], 'logout', "Mtumiaji alitoka")
    session.clear()
    return jsonify({"success": True})

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    msg = data.get('message', '')
    user_id = session['user_id']
    username = session['username']
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
     # Rekodi ujumbe wa mtumiaji
    track_user_action(user_id, session_id, 'send_message', f"Mtumiaji: {msg[:100]}")
    
    save_conversation(user_id, "Mtumiaji", msg)
    history = get_conversation_history(user_id, 10)
    reply = ask_groq(msg, username, history)
    save_conversation(user_id, "Nexora", reply)
    
    # Rekodi jibu la AI
    track_user_action(user_id, session_id, 'ai_response', f"Nexora: {reply[:100]}")
    
    return jsonify({"reply": reply})

@app.route('/api/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    personality = get_personality(user_id)
    game = get_game_state(user_id)
    
    return jsonify({
        "username": session['username'],
        "personality": personality,
        "wins": game['wins'],
        "total_attempts": game['total_attempts']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
```
        
    
    
