import os
import requests
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== GROQ API CONFIGURATION ==========
# 🔥 WEKA GROQ API KEY YAKO HAPA 🔥
GROQ_API_KEY = "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"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Inaweza pia: "llama-3.1-8b-instant" au "mixtral-8x7b-32768"

def ask_groq(question, user_name, conversation_history):
    """Send question to GROQ API and get response"""
    
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
        return get_fallback_response(question, user_name)
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare system prompt - ALWAYS use Swahili
        system_prompt = f"""Wewe ni Nexora AI, chatbot mahiri anayezungumza KISWAHILI TU.
Jina la mtumiaji anayeongea nawe ni {user_name}.

MUHIMU: LAZIMA UJIBU KWA KISWAHILI KILA MARA. HATA MTUMIAJI AKIULIZA KWA KIINGEREZA, WEWE JIBU KWA KISWAHILI.

Tabia zako:
- Jibu kwa ukarimu na heshima
- Tumia emoji kidogo kufurahisha mazungumzo (😊, 🎉, 👍, ❤️)
- Jibu kwa ufupi na kwa usahihi (sentensi 1-3)
- Usijirudie
- Ikiwa hujui jibu, sema tu "Samahani, sijajifunza bado. Unaweza kunifundisha!"

Mazungumzo yaliyopita:
{conversation_history}

Sasa jibu swali la mtumiaji kwa KISWAHILI:"""

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 0.9
        }
        
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "Samahani, sikuelewa. Jaribu tena! 😊")
            return answer.strip()
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            print(f"GROQ API error: {response.status_code} - {error_msg}")
            return get_fallback_response(question, user_name)
            
    except Exception as e:
        print(f"Error calling GROQ: {e}")
        return get_fallback_response(question, user_name)

# ========== FALLBACK RESPONSE (Ikiwa API haifanyi kazi) ==========
def get_fallback_response(question, user_name):
    q = question.lower()
    
    if any(x in q for x in ["habari", "mambo", "vipi", "sasa"]):
        return f"Habari yangu ni nzuri sana, {user_name}! 😊 Na wewe habari yako?"
    
    if any(x in q for x in ["asante", "shukrani"]):
        return f"Karibu sana, {user_name}! 😊 Nafurahi kukusaidia."
    
    if any(x in q for x in ["jina lako", "unaitwa nani"]):
        return f"Naitwa Nexora AI! Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓😊"
    
    return f"Samahani, {user_name}. Sijaelewa vizuri swali lako. Tafadhali jaribu tena! 😊"

# ========== FLASK ROUTES ==========
# Store conversation history per user
conversation_history = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message', '')
    name = data.get('userName', 'Rafiki')
    
    # Initialize conversation history for user
    if name not in conversation_history:
        conversation_history[name] = []
    
    # Get conversation context (last 5 exchanges)
    context = "\n".join(conversation_history[name][-10:])
    
    # Ask GROQ
    reply = ask_groq(msg, name, context)
    
    # Store in history
    conversation_history[name].append(f"Mtumiaji: {msg}")
    conversation_history[name].append(f"Nexora: {reply}")
    
    # Keep only last 10 messages (to avoid token limits)
    if len(conversation_history[name]) > 20:
        conversation_history[name] = conversation_history[name][-20:]
    
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
