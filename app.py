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
app.secret_key = os.environ.get('SECRET_KEY', 'nexora_secret_key_2025')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 24 * 60 * 60
CORS(app, supports_credentials=True)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

DB_NAME = "nexora_users.db"

# ============================================================
# DATABASE SETUP
# ============================================================
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
    print("✅ Database ready")

init_db()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
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
    c.execute("SELECT COUNT(DISTINCT session_id) FROM analytics WHERE date(timestamp) = date('now')")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM conversations")
    total_conv = c.fetchone()[0]
    c.execute("SELECT a.timestamp, u.username, a.action FROM analytics a LEFT JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC LIMIT 15")
    recent = c.fetchall()
    conn.close()
    return {"total_users": total_users, "new_users_week": new_week, "new_users_today": new_today, "active_sessions": active, "total_conversations": total_conv, "recent": recent}

def is_admin(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (uid,))
    r = c.fetchone()
    conn.close()
    return r and r[0] == 'admin'

# ============================================================
# SCHOOL DATA (St. Amedeus)
# ============================================================
SCHOOL_DATA_DIR = 'school_data'
os.makedirs(SCHOOL_DATA_DIR, exist_ok=True)

ANNOUNCEMENTS_FILE = os.path.join(SCHOOL_DATA_DIR, 'announcements.json')
JOBS_FILE = os.path.join(SCHOOL_DATA_DIR, 'jobs.json')
APPLICATIONS_FILE = os.path.join(SCHOOL_DATA_DIR, 'applications.json')

def load_json(f, default):
    if os.path.exists(f):
        with open(f, 'r') as file:
            return json.load(file)
    with open(f, 'w') as file:
        json.dump(default, file)
    return default

def save_json(f, data):
    with open(f, 'w') as file:
        json.dump(data, file, indent=2)

# Initialize school data files if empty
if not os.path.exists(ANNOUNCEMENTS_FILE):
    save_json(ANNOUNCEMENTS_FILE, {"announcements": [
        {"id": 1, "title": "Karibu Shule ya St. Amedeus", "content": "Mwaka mpya wa masomo umeanza. Karibu wanafunzi wote!", "date": datetime.now().strftime('%Y-%m-%d'), "important": True}
    ]})
if not os.path.exists(JOBS_FILE):
    save_json(JOBS_FILE, {"jobs": [
        {"id": 1, "title": "Mwalimu wa Hisabati", "requirements": "Shahada ya Hisabati", "deadline": "2026-12-31"}
    ]})
if not os.path.exists(APPLICATIONS_FILE):
    save_json(APPLICATIONS_FILE, {"applications": []})

# ============================================================
# SCHOOL RESPONSES
# ============================================================
def get_school_answer(q):
    if "historia" in q:
        return "📚 St. Amedeus ilianzishwa mwaka 2001. Ina wanafunzi 800+ na walimu 45. Iko Dar es Salaam, Tanzania."
    if "mission" in q or "dhamira" in q:
        return "🎯 Dhamira: Kutoa elimu bora yenye maadili ya Kikristo."
    if "vision" in q or "maono" in q:
        return "👁️ Maono: Kuwa shule bora zaidi Tanzania."
    if "denis" in q or "mtengenezaji" in q:
        return "👨‍💻 Nimetengenezwa na Denis Albert Mwombeki, mwanafunzi wa St. Amedeus. Ana ujuzi wa programming na ana ndoto kubwa!"
    return None

def process_job_application(msg, name):
    lines = msg.strip().split('\n')
    app = {}
    for line in lines:
        l = line.lower()
        if 'jina:' in l: app['name'] = line.split(':',1)[-1].strip()
        if 'email:' in l: app['email'] = line.split(':',1)[-1].strip()
        if 'nafasi:' in l: app['job'] = line.split(':',1)[-1].strip()
    if app.get('name') and app.get('email'):
        app['date'] = datetime.now().strftime('%Y-%m-%d')
        data = load_json(APPLICATIONS_FILE, {"applications": []})
        data['applications'].append(app)
        save_json(APPLICATIONS_FILE, data)
        return f"✅ Ombi lako limepokelewa {app['name']}! Admin atakujulisha baadaye."
    return None

def get_announcements_response():
    data = load_json(ANNOUNCEMENTS_FILE, {"announcements": []})
    if not data['announcements']:
        return "📢 Hakuna matangazo kwa sasa."
    result = "📢 MATANGAZO YA SHULE:\n\n"
    for a in data['announcements'][:5]:
        result += f"🔹 {a['title']}\n{a['content']}\n📅 {a['date']}\n\n"
    return result

# ============================================================
# AI RESPONSE (GROQ)
# ============================================================
def ask_groq(question, user_name, history):
    if not GROQ_API_KEY:
        return fallback(question, user_name)
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = f"Wewe ni Nexora AI. Jina lako ni NEXORA AI. Ulitengenezwa na Denis Albert Mwombeki, mwanafunzi wa St. Amedeus. Jina la mtumiaji ni {user_name}. Jibu kwa KISWAHILI tu. Tumia emoji. Mazungumzo: {history}"
        payload = {"model": GROQ_MODEL, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": question}], "temperature": 0.7, "max_tokens": 400}
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "Samahani, sikuelewa.")
        return fallback(question, user_name)
    except:
        return fallback(question, user_name)

def fallback(question, user_name):
    q = question.lower()
    if "jina lako" in q or "unaitwa nani" in q:
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert Mwombeki, mwanafunzi wa St. Amedeus. 🎓😊"
    if "habari" in q:
        return f"Habari yangu ni nzuri sana, {user_name}! 😊"
    return f"Samahani, {user_name}. Sijaelewa. Jaribu tena! 😊"

# ============================================================
# STATIC FILES
# ============================================================
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

# ============================================================
# MAIN ROUTES
# ============================================================
@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('chat.html', username=session['username'])
    return render_template('login.html')

@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect('/')
    s = get_stats()
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Admin Stats</title><style>
body{{background:#0f0f13;color:#e4e4e7;font-family:system-ui;padding:20px}}
h1{{color:#c084fc}}.card{{background:#1a1a24;border-radius:16px;padding:20px;margin:10px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px}}
.number{{font-size:2rem;color:#a855f7}}
table{{width:100%;background:#1a1a24;border-radius:16px;border-collapse:collapse}}
th,td{{padding:10px;text-align:left;border-bottom:1px solid #2a2a3a}}
</style></head>
<body><h1>📊 Admin Dashboard</h1>
<div class="grid">
<div class="card"><div class="number">{s['total_users']}</div><div>Jumla Watumiaji</div></div>
<div class="card"><div class="number">{s['new_users_week']}</div><div>Wapya Wiki Hii</div></div>
<div class="card"><div class="number">{s['active_sessions']}</div><div>Vikao Hai Leo</div></div>
<div class="card"><div class="number">{s['total_conversations']}</div><div>Jumla Mazungumzo</div></div>
</div>
<h2>Shughuli za Hivi Karibuni</h2>
<table><thead><tr><th>Muda</th><th>Mtumiaji</th><th>Kitendo</th></tr></thead><tbody>'''
    for r in s['recent']:
        html += f'<tr><td>{r[0]}</td><td>{r[1] or "Anonymous"}</td><td>{r[2]}</td></tr>'
    html += '</tbody></table><br><button onclick="window.location.href=\'/\'" style="background:#a855f7;padding:10px 20px;border:none;border-radius:8px;color:white;cursor:pointer">← Nyuma</button></body></html>'
    return html

@app.route('/admin/school')
def admin_school():
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect('/')
    return render_template('admin_school.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    u = data.get('username', '').strip()
    p = data.get('password', '').strip()
    if not u or not p:
        return jsonify({"success": False, "error": "Jaza nafasi zote"})
    uid = authenticate_user(u, p)
    if uid:
        session.permanent = True
        session['user_id'] = uid
        session['username'] = u
        session['session_id'] = str(uuid.uuid4())
        track_action(uid, session['session_id'], 'login', f"{u} aliingia")
        return jsonify({"success": True, "username": u})
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
    return jsonify({"success": False, "error": "Jina tayari lipo"})

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
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
    
    # Job application submission
    job_result = process_job_application(msg, uname)
    if job_result:
        save_conversation(uid, "Nexora", job_result)
        return jsonify({"reply": job_result})
    
    # Job application form request
    if "kuomba kazi" in msg.lower() or "apply kazi" in msg.lower():
        form = "💼 FOMU YA KUOMBA KAZI\n\nAndika:\nJina: [jina lako]\nEmail: [barua pepe]\nNafasi: [jina la nafasi]"
        save_conversation(uid, "Nexora", form)
        return jsonify({"reply": form})
    
    # School questions
    school_ans = get_school_answer(msg.lower())
    if school_ans:
        save_conversation(uid, "Nexora", school_ans)
        return jsonify({"reply": school_ans})
    
    # Announcements
    if "tangazo" in msg.lower():
        ann = get_announcements_response()
        save_conversation(uid, "Nexora", ann)
        return jsonify({"reply": ann})
    
    # Normal conversation
    history = get_conversation_history(uid, 10)
    reply = ask_groq(msg, uname, history)
    save_conversation(uid, "Nexora", reply)
    track_action(uid, sid, 'ai_response', reply[:100])
    return jsonify({"reply": reply})

@app.route('/api/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"username": session['username']})

# ============================================================
# SCHOOL API ROUTES (for admin_school.html)
# ============================================================
@app.route('/api/school/announcements', methods=['GET'])
def api_get_announcements():
    return jsonify(load_json(ANNOUNCEMENTS_FILE, {"announcements": []}))

@app.route('/api/school/announcements', methods=['POST'])
def api_add_announcement():
    data = request.json
    ann = load_json(ANNOUNCEMENTS_FILE, {"announcements": []})
    new_id = len(ann['announcements']) + 1
    ann['announcements'].append({"id": new_id, "title": data.get('title',''), "content": data.get('content',''), "date": datetime.now().strftime('%Y-%m-%d'), "important": data.get('important',False)})
    save_json(ANNOUNCEMENTS_FILE, ann)
    return jsonify({"success": True})

@app.route('/api/school/announcements/<int:aid>', methods=['DELETE'])
def api_delete_announcement(aid):
    ann = load_json(ANNOUNCEMENTS_FILE, {"announcements": []})
    ann['announcements'] = [a for a in ann['announcements'] if a.get('id') != aid]
    save_json(ANNOUNCEMENTS_FILE, ann)
    return jsonify({"success": True})

@app.route('/api/school/jobs', methods=['GET'])
def api_get_jobs():
    return jsonify(load_json(JOBS_FILE, {"jobs": []}))

@app.route('/api/school/jobs', methods=['POST'])
def api_add_job():
    data = request.json
    jobs = load_json(JOBS_FILE, {"jobs": []})
    new_id = len(jobs['jobs']) + 1
    jobs['jobs'].append({"id": new_id, "title": data.get('title',''), "requirements": data.get('requirements',''), "deadline": data.get('deadline','')})
    save_json(JOBS_FILE, jobs)
    return jsonify({"success": True})

@app.route('/api/school/jobs/<int:jid>', methods=['DELETE'])
def api_delete_job(jid):
    jobs = load_json(JOBS_FILE, {"jobs": []})
    jobs['jobs'] = [j for j in jobs['jobs'] if j.get('id') != jid]
    save_json(JOBS_FILE, jobs)
    return jsonify({"success": True})

@app.route('/api/school/applications', methods=['GET'])
def api_get_applications():
    return jsonify(load_json(APPLICATIONS_FILE, {"applications": []}))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
