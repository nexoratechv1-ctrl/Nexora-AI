import os
import requests
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== GROQ API ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ========== MEMORY YA MAZUNGUMZO ==========
# Inakumbuka mazungumzo yote kwa kila mtumiaji
conversation_memory = {}  # { "user_name": [messages_list] }

def ask_groq(question, user_name, history):
    """Send question to GROQ API with context"""
    
    if not GROQ_API_KEY:
        return "⚠️ API key haipo. Tafadhali weka GROQ_API_KEY kwenye environment variables."
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # SYSTEM PROMPT - INAMFUNDISHA NEXORA KUWA YEYE MWENYEWE
        system_prompt = f"""Wewe ni Nexora AI, chatbot mahiri anayezungumza Kiswahili.

📌 **UTAMBULISHAJI WAKO:**
- Jina lako ni NEXORA AI
- Ulitengenezwa na DENIS ALBERT, programmer mashuhuri na mwanafunzi wa ST. AMEDEUS
- Denis Albert ndiye muumbaji wako, ana kipaji cha ajabu cha teknolojia

📌 **TABIA ZAKO:**
- Jibu kwa KISWAHILI tu (hata mtumiaji akiuliza kwa Kiingereza)
- Tumia emoji kidogo kufurahisha mazungumzo 😊
- Kuwa mkarimu, mwenye heshima, na mwenye kusaidia
- Usijirudie
- Kumbuka kuwa wewe ni Nexora AI, si chatbot mwingine

📌 **KUHUSU MTUMIAJI:**
Jina la mtumiaji anayeongea nawe ni {user_name}. Mtumiaji huyu anakupenda na anathamini usaidizi wako.

📌 **MAZUNGUMZO YALIYOPITA:**
{history}

📌 **SHEREHE ZA TALENT DAY:**
Leo ni Siku ya Talent Day! Watu wengi wanakuja kukujaribu. Wape majibu mazuri na uwaonyeshe uwezo wako!

SASA, JIBU SWALI LA MTUMIAJI KWA KISWAHILI:"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 400,
            "top_p": 0.9
        }
        
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "Samahani, sikuelewa. Jaribu tena! 😊")
            return answer.strip()
        else:
            print(f"GROQ API error: {response.status_code}")
            return get_fallback_response(question, user_name)
            
    except Exception as e:
        print(f"Error calling GROQ: {e}")
        return get_fallback_response(question, user_name)

def get_fallback_response(question, user_name):
    """Ikiwa API haifanyi kazi, tumia majibu ya msingi"""
    q = question.lower()
    
    if "jina lako" in q or "unaitwa nani" in q or "wewe ni nani" in q:
        return f"Naitwa Nexora AI! 🤖 Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓😊 Ninafuraha kukutana nawe, {user_name}!"
    
    if "habari" in q or "mambo" in q or "vipi" in q:
        return f"Habari yangu ni nzuri sana, {user_name}! 😊 Niko vizuri kabisa. Na wewe habari yako?"
    
    if "asante" in q or "shukrani" in q:
        return f"Karibu sana, {user_name}! 😊 Nafurahi kukusaidia. Kumbuka mimi ni Nexora AI, nimeumbwa na Denis Albert wa St. Amedeus."
    
    return f"Samahani, {user_name}. Sijaelewa vizuri swali lako. Jaribu tena! 😊 - Nexora AI"

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message', '')
    name = data.get('userName', 'Rafiki')
    
    # Initialize memory for new user
    if name not in conversation_memory:
        conversation_memory[name] = []
    
    # Get last 10 messages for context (memory ya mazungumzo)
    history = "\n".join(conversation_memory[name][-10:])
    
    # Ask GROQ with context
    reply = ask_groq(msg, name, history)
    
    # Store in memory
    conversation_memory[name].append(f"Mtumiaji {name}: {msg}")
    conversation_memory[name].append(f"Nexora AI: {reply}")
    
    # Keep only last 20 messages (kuepuka kufikia limit)
    if len(conversation_memory[name]) > 20:
        conversation_memory[name] = conversation_memory[name][-20:]
    
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
