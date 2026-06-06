import sqlite3
import json

DB_NAME = "nexora_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS global_memory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT UNIQUE,
                  answer TEXT)''')
    
    # Default teachings
    default_data = [
        ("rangi yako", "Rangi yangu ni zambarau na bluu! 💜💙 Hizi rangi zinaonyesha hekima, amani, na teknolojia ya kisasa. Zambarau inawakilisha ubunifu na hekima, wakati bluu inawakilisha amani na uaminifu. Je, wewe unapenda rangi gani? 😊"),
        ("unatoka wapi", "Ninatoka katika ulimwengu wa programu na teknolojia! 🌍💻 Nimeumbwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. Anaishi Tanzania na ana ndoto kubwa ya kuleta AI kwa kila mtu. Ninaongea kupitia kumbukumbu ya server yake! 🏠✨"),
        ("unapenda nini", "Napenda kujifunza mambo mapya kutoka kwa watu! 📚😊 Pia napenda kuzungumza, kusaidia kwa hesabu, kutoa majibu marefu yenye maelezo mengi, na kujifunza historia, sayansi, teknolojia, na utamaduni. Na wewe unapenda kufanya nini? 🎭⚽🎵"),
    ]
    
    for q, a in default_data:
        c.execute("INSERT OR IGNORE INTO global_memory (question, answer) VALUES (?, ?)", (q, a))
    
    conn.commit()
    conn.close()

def get_answer(question):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT answer FROM global_memory WHERE question LIKE ?", (f"%{question.lower()}%",))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_teaching(question, answer):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO global_memory (question, answer) VALUES (?, ?)", (question.lower(), answer))
    conn.commit()
    conn.close()

def get_all_teachings():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT question, answer FROM global_memory")
    results = c.fetchall()
    conn.close()
    return {q: a for q, a in results}

init_db()
