import os
import re
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from difflib import get_close_matches

app = Flask(__name__)
CORS(app)

# ========== DATABASE SETUP ==========
DB_NAME = "nexora.db"

# Cache for teachings
teachings_cache = {}
# Cache ya maneno yote kwa ajili ya spelling correction
all_keywords = []

def load_cache():
    global teachings_cache, all_keywords
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT question, answer FROM teachings")
    rows = c.fetchall()
    teachings_cache = {q: a for q, a in rows}
    all_keywords = list(teachings_cache.keys())
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
            ("sayansi", "Sayansi ni njia ya kuelewa ulimwengu wetu kwa kutumia uchunguzi, majaribio, na mantiki. Inajumuisha fizikia, kemia, biolojia, na matawi mengine. 🔬✨"),
            ("fizikia", "Fizikia ni tawi la sayansi linalochunguza nguvu, mwendo, nishati, na sheria zinazotawala ulimwengu. Inasaidia kuelezea jinsi vitu vinavyofanya kazi! ⚡🔭"),
            ("kemia", "Kemia ni tawi la sayansi linalochunguza vitu, muundo wake, na mabadiliko yanayotokea. Inahusika na molekuli, atomi, na athari za kemikali! 🧪⚗️"),
            ("biolojia", "Biolojia ni tawi la sayansi linalochunguza viumbe hai, mimea, wanyama, na wanadamu. Inaelezea jinsi viumbe wanavyoishi, kukua, na kuzaliana! 🌱🐘"),
        ]
        for q, a in defaults:
            c.execute("INSERT OR IGNORE INTO teachings (question, answer) VALUES (?, ?)", (q, a))
    
    conn.commit()
    conn.close()
    load_cache()

def save_teaching(question, answer):
    global teachings_cache, all_keywords
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO teachings (question, answer) VALUES (?, ?)", 
              (question.lower().strip(), answer.strip()))
    conn.commit()
    conn.close()
    teachings_cache[question.lower().strip()] = answer.strip()
    all_keywords = list(teachings_cache.keys())

# ========== SMART SPELLING CORRECTION & KEYWORD DETECTION ==========
def correct_spelling(word):
    """Correct spelling of a single word based on known keywords"""
    if word in all_keywords:
        return word
    
    # Find closest match (80% similarity threshold)
    matches = get_close_matches(word, all_keywords, n=1, cutoff=0.7)
    if matches:
        return matches[0]
    return word

def get_smart_answer(question):
    """
    Super smart answer detection:
    - Corrects spelling errors
    - Detects any keyword from teachings
    - Understands different phrasing
    """
    q_lower = question.lower().strip()
    
    # FIRST: Exact match
    if q_lower in teachings_cache:
        return teachings_cache[q_lower]
    
    # SECOND: Break question into words and correct spelling of each word
    words = re.findall(r'\b\w+\b', q_lower)
    
    # Correct spelling of each word
    corrected_words = [correct_spelling(word) for word in words]
    
    # Check if any corrected word matches a teaching keyword
    for word in corrected_words:
        if word in teachings_cache:
            return teachings_cache[word]
    
    # THIRD: Check if question contains any teaching key (as phrase)
    # Sort by length (longest first) for best match
    sorted_keys = sorted(teachings_cache.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        # Direct containment
        if key in q_lower:
            return teachings_cache[key]
        
        # Check with spelling correction on the key
        corrected_key = correct_spelling(key)
        if corrected_key != key and corrected_key in q_lower:
            return teachings_cache[key]
    
    # FOURTH: Check if any teaching key is similar to any word in question
    for key in sorted_keys:
        # Split key into words
        key_words = key.split()
        for kw in key_words:
            # Check if key word is similar to any word in question
            for q_word in words:
                if get_close_matches(q_word, [kw], n=1, cutoff=0.7):
                    return teachings_cache[key]
    
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
        # Check for math pattern
        if re.search(r'\d+[\+\-\*\/]\d+', expr):
            result = eval(expr)
            return f"📊 {result}"
    except:
        pass
    return None

# ========== CONVERSATION RESPONSES ==========
def get_conversation_response(question, name):
    q = question.lower()
    
    # Greetings
    if any(x in q for x in ["habari", "mambo", "vipi", "how are", "hello", "hi", "sasa"]):
        return f"Habari yangu ni nzuri sana, {name}! 😊 Niko vizuri kabisa. Na wewe habari yako?"
    
    # Thanks
    if any(x in q for x in ["asante", "shukrani", "thank"]):
        return f"Karibu sana, {name}! 😊 Nafurahi kukusaidia."
    
    # Self introduction
    if any(x in q for x in ["jina lako", "unaitwa nani", "wewe ni nani", "who are you"]):
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓😊"
    
    # Default
    return f"Samahani, {name}. Sijajifunza jibu la swali hili bado. Unaweza kunifundisha kwa kusema 'Unapoulizwa [swali] jibu [jibu]' 😊"

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
    
    # STEP 2: Smart answer with spelling correction
    smart_answer = get_smart_answer(msg)
    if smart_answer:
        return jsonify({"reply": smart_answer})
    
    # STEP 3: Check math
    math_result = calculate_math(msg)
    if math_result:
        return jsonify({"reply": math_result})
    
    # STEP 4: Conversation response
    response = get_conversation_response(msg, name)
    return jsonify({"reply": response})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
