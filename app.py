import os
import re
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== DATABASE SETUP ==========
DB_NAME = "nexora.db"

# Cache for teachings
teachings_cache = {}

def load_cache():
    """Load all teachings from database into memory cache"""
    global teachings_cache
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT question, answer FROM teachings")
    rows = c.fetchall()
    teachings_cache = {q: a for q, a in rows}
    conn.close()
    print(f"✅ Loaded {len(teachings_cache)} teachings into cache")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS teachings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT UNIQUE,
                  answer TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM teachings")
    if c.fetchone()[0] == 0:
        defaults = [
            ("jina lako", "Naitwa Nexora AI! Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓🚀"),
            ("unaitwa nani", "Mimi ni Nexora AI! Nimetengenezwa na Denis Albert, mwanafunzi wa St. Amedeus. 😊"),
            ("rangi yako", "Rangi yangu ni zambarau na bluu! 💜💙"),
            ("physics-89", "Physics-89 inaweza kumaanisha kozi ya fizikia ya mwaka 1989 au daraja la 89% kwenye fizikia. Hakuna taarifa maalum zaidi. 😊"),
        ]
        for q, a in defaults:
            c.execute("INSERT OR IGNORE INTO teachings (question, answer) VALUES (?, ?)", (q, a))
    
    conn.commit()
    conn.close()
    load_cache()

def save_teaching(question, answer):
    global teachings_cache
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO teachings (question, answer) VALUES (?, ?)", 
              (question.lower().strip(), answer.strip()))
    conn.commit()
    conn.close()
    teachings_cache[question.lower().strip()] = answer.strip()

def get_answer_from_cache(question):
    """
    Get answer directly from cache - returns ONLY ONE answer (the best match)
    Does NOT list all teachings
    """
    q_lower = question.lower().strip()
    
    # FIRST: Try exact match
    if q_lower in teachings_cache:
        return teachings_cache[q_lower]
    
    # SECOND: Try to find if question contains any teaching key
    # But return ONLY THE FIRST match, not all
    for key, answer in teachings_cache.items():
        if key in q_lower:
            return answer  # Return first match only
    
    # THIRD: Try if any teaching key is contained in question
    for key, answer in teachings_cache.items():
        if q_lower in key:
            return answer  # Return first match only
    
    return None

# ========== PROCESS MULTIPLE TEACHINGS ==========
def process_multiple_teachings(message):
    teachings = []
    lines = message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        lower_line = line.lower()
        
        if "unapoulizwa" in lower_line and "jibu" in lower_line:
            parts = lower_line.split("jibu")
            if len(parts) >= 2:
                trigger = parts[0].replace("unapoulizwa", "").strip()
                answer = parts[1].strip()
                if trigger and answer:
                    teachings.append((trigger, answer))
        
        elif "=" in line and not lower_line.startswith("unapoulizwa"):
            parts = line.split("=")
            if len(parts) == 2:
                trigger = parts[0].strip()
                answer = parts[1].strip()
                if trigger and answer:
                    teachings.append((trigger, answer))
    
    return teachings

# ========== MATH ==========
def calculate_math(question):
    try:
        expr = question.lower().replace("ni nini", "").replace("je", "").replace("?", "")
        expr = expr.replace("×", "*").replace("÷", "/").replace("x", "*")
        if re.search(r'\d+[\+\-\*\/]\d+', expr):
            result = eval(expr)
            return f"📊 {result}"
    except:
        pass
    return None

# ========== DIRECT RESPONSES (NO TEACHING RECALL) ==========
def get_direct_response(question, name):
    q = question.lower()
    
    if "jina lako" in q or "unaitwa nani" in q:
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓😊"
    
    if "habari" in q or "mambo" in q:
        return f"Habari yangu ni nzuri sana, {name}! 😊 Niko vizuri kabisa. Na wewe habari yako?"
    
    if "asante" in q:
        return f"Karibu sana, {name}! 😊 Nafurahi kukusaidia."
    
    if "mwezi" in q:
        return "Mwezi ni satelaiti asilia ya Dunia. Umbali: km 384,400. Watu walitua mwezini mwaka 1969! 🌕"
    
    if "tanzania" in q or "nyerere" in q:
        return "Tanzania nchi yenye historia tajiri! Mlima Kilimanjaro mrefu zaidi Afrika (mita 5,895). Mwalimu Nyerere alikuwa baba wa taifa. 🇹🇿"
    
    if "ai" in q or "akili bandia" in q:
        return "AI (Akili Bandia) ni teknolojia inayojifunza kutoka kwa data. Mimi ni Nexora AI, nimeumbwa na Denis Albert. 🤖"
    
    return f"Samahani, {name}. Sijajifunza jibu la swali hili bado. 😊"

# ========== FLASK ROUTES ==========
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message', '')
    name = data.get('userName', 'Rafiki')
    
    # STEP 1: Process teachings (when user is teaching)
    teachings = process_multiple_teachings(msg)
    
    if teachings:
        saved_count = 0
        for question, answer in teachings:
            save_teaching(question, answer)
            saved_count += 1
        
        if saved_count == 1:
            reply = f"✅ Nimekumbuka!\n\n'{teachings[0][0]}' → imehifadhiwa"
        else:
            reply = f"✅ Nimekumbuka {saved_count} mafundisho!"
        return jsonify({"reply": reply})
    
    # STEP 2: Get answer from CACHE (ONE answer only)
    cached_answer = get_answer_from_cache(msg)
    if cached_answer:
        return jsonify({"reply": cached_answer})
    
    # STEP 3: Check math
    math_result = calculate_math(msg)
    if math_result:
        return jsonify({"reply": math_result})
    
    # STEP 4: Direct response (no teaching recall)
    response = get_direct_response(msg, name)
    return jsonify({"reply": response})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
