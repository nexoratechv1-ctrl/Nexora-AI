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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nexora_secret_key_2025_talent_day')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 24 * 60 * 60
CORS(app, supports_credentials=True)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

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
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS personality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal TEXT NOT NULL,
        trait TEXT NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        wins INTEGER DEFAULT 0,
        total_attempts INTEGER DEFAULT 0,
        current_game_number INTEGER,
        current_game_attempts INTEGER DEFAULT 0,
        game_active INTEGER DEFAULT 0,
        last_played TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        session_id TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def create_user(u, p):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, hash_password(p)))
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return uid
    except:
        conn.close()
        return None

def authenticate_user(u, p):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (u, hash_password(p)))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def save_conversation(uid, role, msg):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, role, message) VALUES (?, ?, ?)", (uid, role, msg))
    conn.commit()
    conn.close()

def get_conversation_history(uid, limit=20):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, message FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (uid, limit))
    rows = c.fetchall()
    conn.close()
    h = []
    for r, m in reversed(rows):
        h.append(f"{r}: {m}")
    return "\n".join(h)

def save_personality(uid, animal, trait):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM personality WHERE user_id = ?", (uid,))
    c.execute("INSERT INTO personality (user_id, animal, trait) VALUES (?, ?, ?)", (uid, animal, trait))
    conn.commit()
    conn.close()

def get_personality(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT animal, trait FROM personality WHERE user_id = ? ORDER BY date DESC LIMIT 1", (uid,))
    r = c.fetchone()
    conn.close()
    return r if r else None

def get_game_state(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT wins, total_attempts, current_game_number, current_game_attempts, game_active FROM game_stats WHERE user_id = ?", (uid,))
    r = c.fetchone()
    conn.close()
    if r:
        return {"wins": r[0], "total_attempts": r[1], "number": r[2], "attempts": r[3], "active": r[4]}
    return {"wins": 0, "total_attempts": 0, "number": None, "attempts": 0, "active": False}

def update_game_state(uid, wins=None, total_attempts=None, number=None, attempts=None, active=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM game_stats WHERE user_id = ?", (uid,))
    exists = c.fetchone()
    if exists:
        ups = []
        vals = []
        if wins is not None:
            ups.append("wins = ?")
            vals.append(wins)
        if total_attempts is not None:
            ups.append("total_attempts = ?")
            vals.append(total_attempts)
        if number is not None:
            ups.append("current_game_number = ?")
            vals.append(number)
        if attempts is not None:
            ups.append("current_game_attempts = ?")
            vals.append(attempts)
        if active is not None:
            ups.append("game_active = ?")
            vals.append(active)
        ups.append("last_played = CURRENT_TIMESTAMP")
        if ups:
            vals.append(uid)
            c.execute(f"UPDATE game_stats SET {', '.join(ups)} WHERE user_id = ?", vals)
    else:
        c.execute("INSERT INTO game_stats (user_id, wins, total_attempts, current_game_number, current_game_attempts, game_active, last_played) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (uid, wins or 0, total_attempts or 0, number, attempts or 0, 1 if active else 0))
    conn.commit()
    conn.close()

def track_action(uid, sid, action, details=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO analytics (user_id, session_id, action, details) VALUES (?, ?, ?, ?)", (uid, sid, action, details))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE created_at > date('now', '-7 days')")
    new_week = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
    new_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM conversations")
    total_conv = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM conversations WHERE date(timestamp) = date('now')")
    conv_today = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT session_id) FROM analytics WHERE date(timestamp) = date('now')")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM personality")
    personality_count = c.fetchone()[0]
    c.execute("SELECT a.timestamp, u.username, a.action, a.details FROM analytics a LEFT JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC LIMIT 20")
    recent = c.fetchall()
    conn.close()
    return {"total_users": total_users, "new_users_week": new_week, "new_users_today": new_today, "total_conversations": total_conv, "conversations_today": conv_today, "active_sessions_today": active, "personality_count": personality_count, "recent_activity": recent}

def is_admin(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (uid,))
    r = c.fetchone()
    conn.close()
    return r and (r[0] == 'admin' or uid == 1)

def generate_image(prompt):
    try:
        clean = prompt.replace("chora", "").replace("picha ya", "").replace("draw", "").strip()
        enc = requests.utils.quote(clean)
        return f"https://image.pollinations.ai/prompt/{enc}?width=512&height=512&nologo=true"
    except:
        return None

def personality_result(answers):
    if answers.get('likes_night') and answers.get('likes_flying'):
        return {"animal": "Bundi 🦉", "trait": "Una hekima na utulivu."}
    elif answers.get('likes_night') and not answers.get('likes_flying'):
        return {"animal": "Paka 🐱", "trait": "Mpenda faragha, unajitegemea."}
    elif not answers.get('likes_night') and answers.get('likes_flying'):
        return {"animal": "Ndege 🦅", "trait": "Una roho ya uhuru."}
    elif not answers.get('likes_night') and answers.get('likes_people'):
        return {"animal": "Simba 🦁", "trait": "Una uongozi na ujasiri."}
    else:
        return {"animal": "Tembo 🐘", "trait": "Una hekima na uaminifu."}

def ask_groq(question, user_name, history):
    if not GROQ_API_KEY:
        return fallback(question, user_name)
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = f"Wewe ni Nexora AI. Jina lako ni NEXORA AI. Ulitengenezwa na DENIS ALBERT, mwanafunzi wa ST. AMEDEUS. Jina la mtumiaji ni {user_name}. Jibu kwa KISWAHILI tu. Tumia emoji kidogo. Mazungumzo yaliyopita: {history}"
        payload = {"model": GROQ_MODEL, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": question}], "temperature": 0.7, "max_tokens": 400}
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "Samahani, sikuelewa.")
        else:
            return fallback(question, user_name)
    except:
        return fallback(question, user_name)

def fallback(question, user_name):
    q = question.lower()
    if "jina lako" in q or "unaitwa nani" in q:
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert, mwanafunzi wa St. Amedeus. 🎓😊"
    if "habari" in q:
        return f"Habari yangu ni nzuri sana, {user_name}! 😊"
    return f"Samahani, {user_name}. Sijaelewa vizuri. Jaribu tena! 😊"

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/static/icon-512.png')
def generate_icon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" fill="#a855f7" rx="100"/><text x="256" y="380" font-family="Arial" font-size="380" font-weight="bold" fill="white" text-anchor="middle">N</text></svg>'
    return svg, 200, {'Content-Type': 'image/svg+xml'}

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chat.html', username=session['username'])
    return render_template('login.html')

@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session:
        return redirect('/')
    if not is_admin(session['user_id']):
        return "<h2>⛔ Huna ruhusa.</h2><p><a href='/'>Rudi</a></p>", 403
    s = get_stats()
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nexora AI - Admin</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#0f0f13;color:#e4e4e7;padding:20px}}.container{{max-width:1200px;margin:0 auto}}h1{{color:#c084fc;margin-bottom:20px}}.admin-badge{{background:#ef4444;color:#fff;padding:4px 12px;border-radius:20px;font-size:.8rem;margin-left:10px}}.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:20px;margin-bottom:30px}}.stat-card{{background:#1a1a24;border-radius:16px;padding:20px;text-align:center;border:1px solid #2a2a3a}}.stat-number{{font-size:2.5rem;font-weight:bold;color:#a855f7}}.stat-label{{color:#a1a1aa;margin-top:8px}}table{{width:100%;background:#1a1a24;border-radius:16px;border-collapse:collapse}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #2a2a3a}}th{{background:#2a2a3a;color:#c084fc}}.btn{{background:#a855f7;border:none;border-radius:8px;padding:10px 20px;color:#fff;cursor:pointer;margin-bottom:20px;margin-right:10px}}.logout{{background:#ef4444}}
</style>
</head>
<body>
<div class="container"><div><button class="btn" onclick="window.location.href='/'">← Nyuma</button><button class="btn logout" onclick="logout()">🚪 Toka</button></div>
<h1>📊 Admin Dashboard <span class="admin-badge">ADMIN</span></h1>
<div class="stats-grid">
<div class="stat-card"><div class="stat-number">{s['total_users']}</div><div class="stat-label">Jumla Watumiaji</div></div>
<div class="stat-card"><div class="stat-number">{s['new_users_week']}</div><div class="stat-label">Wapya Wiki Hii</div></div>
<div class="stat-card"><div class="stat-number">{s['new_users_today']}</div><div class="stat-label">Wapya Leo</div></div>
<div class="stat-card"><div class="stat-number">{s['active_sessions_today']}</div><div class="stat-label">Vikao Hai Leo</div></div>
<div class="stat-card"><div class="stat-number">{s['total_conversations']}</div><div class="stat-label">Jumla Mazungumzo</div></div>
<div class="stat-card"><div class="stat-number">{s['conversations_today']}</div><div class="stat-label">Mazungumzo Leo</div></div>
<div class="stat-card"><div class="stat-number">{s['personality_count']}</div><div class="stat-label">Personality Test</div></div>
</div>
<h2>📝 Shughuli za Hivi Karibuni</h2>
<div style="overflow-x:auto;"><table><thead><tr><th>Muda</th><th>Mtumiaji</th><th>Kitendo</th><th>Maelezo</th></tr></thead><tbody>'''
    for act in s['recent_activity']:
        html += f'<tr><td>{act[0]}</td><td>{act[1] or "Anonymous"}</td><td>{act[2]}</td><td>{str(act[3])[:50] if act[3] else "-"}</td></tr>'
    html += '''</tbody></table></div></div>
<script>async function logout(){await fetch('/api/logout',{method:'POST'});window.location.href='/';}</script>
</body></html>'''
    return html

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    u = data.get('username', '').strip()
    p = data.get('password', '').strip()
    rm = data.get('rememberMe', False)
    if not u or not p:
        return jsonify({"success": False, "error": "Jaza nafasi zote"})
    uid = authenticate_user(u, p)
    if uid:
        session.permanent = rm
        session['user_id'] = uid
        session['username'] = u
        session['session_id'] = str(uuid.uuid4())
        track_action(uid, session['session_id'], 'login', f"{u} aliingia")
        return jsonify({"success": True, "username": u})
    else:
        return jsonify({"success": False, "error": "Jina au password si sahihi"})

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    u = data.get('username', '').strip()
    p = data.get('password', '').strip()
    if not u or not p:
        return jsonify({"success": False, "error": "Jaza nafasi zote"})
    if len(p) < 4:
        return jsonify({"success": False, "error": "Password lazima iwe na herufi 4 au zaidi"})
    uid = create_user(u, p)
    if uid:
        session.permanent = True
        session['user_id'] = uid
        session['username'] = u
        session['session_id'] = str(uuid.uuid4())
        track_action(uid, session['session_id'], 'signup', f"{u} alijisajili")
        return jsonify({"success": True, "username": u})
    else:
        return jsonify({"success": False, "error": "Jina la mtumiaji tayari lipo"})

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session and 'session_id' in session:
        track_action(session['user_id'], session['session_id'], 'logout', "Alitoka")
    session.clear()
    return jsonify({"success": True})

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    msg = data.get('message', '')
    uid = session['user_id']
    uname = session['username']
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    sid = session['session_id']
    track_action(uid, sid, 'send_message', msg[:100])
    save_conversation(uid, "Mtumiaji", msg)
    history = get_conversation_history(uid, 10)
    reply = ask_groq(msg, uname, history)
    save_conversation(uid, "Nexora", reply)
    track_action(uid, sid, 'ai_response', reply[:100])
    return jsonify({"reply": reply})

@app.route('/api/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    uid = session['user_id']
    p = get_personality(uid)
    g = get_game_state(uid)
    return jsonify({"username": session['username'], "personality": p, "wins": g['wins'], "total_attempts": g['total_attempts']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
