import os
import requests
import json
import random
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== GROQ API CONFIGURATION ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ========== MEMORY STORAGE ==========
conversation_memory = {}      # Kumbukumbu ya mazungumzo
user_voice_memory = {}        # #1: Kumbukumbu ya sauti na majina
user_personality = {}         # #3: Kumbukumbu ya personality test
game_numbers = {}             # #4: Kumbukumbu ya mchezo wa namba

# ========== FEATURE #8: IMAGE GENERATION (Pollinations AI - BURE KABISA) ==========
def generate_image(prompt):
    """Generate image using Pollinations AI (free, no API key required)"""
    try:
        # Clean the prompt
        clean_prompt = prompt.replace("chora", "").replace("picha ya", "").replace("draw", "").replace("picture of", "").strip()
        # Encode for URL
        encoded_prompt = requests.utils.quote(clean_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
        return image_url
    except Exception as e:
        print(f"Image generation error: {e}")
        return None

# ========== FEATURE #3: PERSONALITY TEST LOGIC ==========
def personality_test_result(answers):
    """Determine animal based on answers"""
    likes_night = answers.get('likes_night', False)
    likes_flying = answers.get('likes_flying', False)
    likes_people = answers.get('likes_people', False)
    
    if likes_night and likes_flying:
        return {"animal": "Bundi 🦉", "trait": "Una hekima na utulivu. Wewe ni mwenye busara na unaona yale wasiyoyaona wengine! Unapenda kufanya kazi usiku na kuwa na amani."}
    elif likes_night and not likes_flying:
        return {"animal": "Paka 🐱", "trait": "Wewe ni mwenye ustaarabu, mpenda faragha, na unajitegemea. Unapenda uhuru wako na wakati wa peke yako!"}
    elif not likes_night and likes_flying:
        return {"animal": "Ndege 🦅", "trait": "Una roho ya uhuru, unapenda kusafiri na kuchunguza mambo mapya. Wewe ni mwenye ujasiri na unapenda anga za juu!"}
    elif not likes_night and likes_people:
        return {"animal": "Simba 🦁", "trait": "Una uongozi, ujasiri, na unapenda kuwa katikati ya watu. Wewe ni mfalme/malkia wa kundi lako!"}
    else:
        return {"animal": "Tembo 🐘", "trait": "Una hekima, uaminifu, na unakumbuka mambo mengi. Wewe ni mlinzi wa familia yako na unaheshimika sana!"}

# ========== FEATURE #3: PERSONALITY TEST FUNCTIONS ==========
def start_personality_test(user_name):
    user_personality[user_name] = {'stage': 'awaiting_answer1'}
    return f"""😊 **KARIBU KWENYE TEST YA MNYAMA WAKO WA NDANI, {user_name}!** 🦁🐘🦉

📝 **Swali la 1/3:** Unapenda usiku au mchana?
🔹 Andika: "Usiku" au "Mchana"

💡 Kidokezo: Chagua moja tu kati ya hizo mbili!"""

def personality_test_question2(user_name):
    user_personality[user_name]['stage'] = 'awaiting_answer2'
    return f"""😊 **Swali la 2/3, {user_name}!** 

📝 Ungependa kuruka angani au kuogelea baharini?
🔹 Andika: "Kuruka" au "Kuogelea"

💡 Kidokezo: Chagua kulingana na kile ungependa zaidi!"""

def personality_test_question3(user_name):
    user_personality[user_name]['stage'] = 'awaiting_answer3'
    return f"""😊 **Swali la mwisho, {user_name}!** 

📝 Unapenda kuwa na watu wengi au faragha?
🔹 Andika: "Watu wengi" au "Faragha"

💡 Kidokezo: Jibu kwa uaminifu!"""

def process_personality_result(user_name, answer):
    # Determine answers based on user's responses
    user_data = user_personality.get(user_name, {})
    result = personality_test_result({
        'likes_night': user_data.get('answer1') == 'usiku',
        'likes_flying': user_data.get('answer2') == 'kuruka',
        'likes_people': answer == 'watu wengi'
    })
    user_personality[user_name] = {'stage': 'completed', 'result': result}
    return f"""🎉 **MATOKEO YAKO, {user_name}!** 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐘 **Wewe ni {result['animal']}** 

📝 **Tabia yako:**
{result['trait']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
😊 Asante kwa kushiriki! Unaweza kuanza mazungumzo mengine au kujaribu feature nyingine."""

# ========== FEATURE #4: NUMBER GUESSING GAME ==========
def start_number_game(user_name):
    number = random.randint(1, 100)
    game_numbers[user_name] = {'number': number, 'attempts': 0, 'active': True}
    return f"""🔢 **NIMEKUWA NA NAMBA KATIKA AKILI YANGU!** 🎯
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nimefikiria namba kati ya **1 na 100**. 
Una majaribio mengi kama utakavyohitaji!

🔹 **Jaribu kukisia:** Andika namba tu (mfano: 42)

💡 Kidokezo: Nitasema "Juu" au "Chini" kukusaidia kupata namba sahihi!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Anza kukisia sasa!"""

def handle_number_game(user_name, guess_text):
    game = game_numbers.get(user_name, {})
    if not game.get('active'):
        return None
    
    try:
        # Extract number from text
        import re
        numbers = re.findall(r'\d+', guess_text)
        if not numbers:
            return "🔢 Tafadhali andika namba tu (mfano: 42) ili kukisia!"
        
        guess = int(numbers[0])
        game['attempts'] += 1
        target = game['number']
        
        if guess < target:
            return f"📈 **Juu!** Namba yangu ni kubwa kuliko {guess}. Jaribu tena! (Majaribio: {game['attempts']})"
        elif guess > target:
            return f"📉 **Chini!** Namba yangu ni ndogo kuliko {guess}. Jaribu tena! (Majaribio: {game['attempts']})"
        else:
            game['active'] = False
            return f"""🎉 **UMESHINDA!** 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 Namba yangu ilikuwa **{target}**!
📊 Umekisia baada ya majaribio {game['attempts']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Ungependa kucheza tena? Andika 'Ndio' au 'Hapana'."""
    except ValueError:
        return "🔢 Tafadhali andika namba tu (mfano: 42) ili kukisia!"

def stop_number_game(user_name):
    if user_name in game_numbers:
        del game_numbers[user_name]
    return "✅ Mchezo umefungwa. Unaweza kuanza mazungumzo mengine! 😊"

# ========== GROQ API CALL ==========
def ask_groq(question, user_name, history):
    """Send question to GROQ API with context"""
    
    if not GROQ_API_KEY:
        return get_fallback_response(question, user_name)
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # System prompt - teaches Nexora who he is
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
Jina la mtumiaji anayeongea nawe ni {user_name}.

📌 **MAZUNGUMZO YALIYOPITA:**
{history}

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
    """Fallback responses when API is unavailable"""
    q = question.lower()
    
    if "jina lako" in q or "unaitwa nani" in q or "wewe ni nani" in q:
        return f"Naitwa Nexora AI! 🤖 Nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus. 🎓😊 Ninafuraha kukutana nawe, {user_name}!"
    
    if "habari" in q or "mambo" in q or "vipi" in q:
        return f"Habari yangu ni nzuri sana, {user_name}! 😊 Niko vizuri kabisa. Na wewe habari yako?"
    
    if "asante" in q or "shukrani" in q:
        return f"Karibu sana, {user_name}! 😊 Nafurahi kukusaidia. Kumbuka mimi ni Nexora AI, nimeumbwa na Denis Albert wa St. Amedeus."
    
    return f"Samahani, {user_name}. Sijaelewa vizuri swali lako. Jaribu tena! 😊 - Nexora AI"

# ========== FEATURE #1: VOICE RECOGNITION & MEMORY ==========
def recognize_user(user_name):
    """Simple user recognition based on name"""
    if user_name and user_name in user_voice_memory:
        return user_voice_memory[user_name]
    return None

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message', '')
    name = data.get('userName', 'Rafiki')
    
    q = msg.lower().strip()
    
    # ========== FEATURE #1: VOICE RECOGNITION ==========
    if name not in user_voice_memory:
        user_voice_memory[name] = name
    
    # ========== FEATURE #8: IMAGE GENERATION ==========
    if q.startswith("chora") or q.startswith("picha ya") or q.startswith("draw") or q.startswith("picture of"):
        prompt = msg.replace("chora", "").replace("picha ya", "").replace("draw", "").replace("picture of", "").strip()
        if prompt:
            image_url = generate_image(prompt)
            if image_url:
                return jsonify({
                    "reply": f"🎨 **Picha yako ya '{prompt}' imetengenezwa!**\n\n🖼️ [Bonyeza hapa kuona picha]({image_url})\n\n😊 Asante kwa kuuliza! Nakutakia siku njema!",
                    "image": image_url
                })
            else:
                return jsonify({"reply": "Samahani, sikuweza kutengeneza picha. Jaribu tena kwa maneno tofauti! 😊"})
        else:
            return jsonify({"reply": "Tafadhali niambie nichore nini! Kwa mfano: 'Chora simba' au 'Picha ya mlima' 🎨"})
    
    # ========== FEATURE #4: NUMBER GAME ==========
    if q == "cheza namba" or q == "game ya namba" or q == "namba game" or q == "start game":
        reply = start_number_game(name)
        return jsonify({"reply": reply})
    
    if q == "kata game" or q == "stop game" or q == "maliza game":
        reply = stop_number_game(name)
        return jsonify({"reply": reply})
    
    if name in game_numbers and game_numbers[name].get('active', False):
        # Check if user wants to play again after winning
        if "ndio" in q or "yes" in q:
            # Start new game
            if not game_numbers[name].get('active', True):
                del game_numbers[name]
                reply = start_number_game(name)
                return jsonify({"reply": reply})
        elif "hapana" in q or "no" in q:
            reply = stop_number_game(name)
            return jsonify({"reply": reply})
        
        # Handle guess
        result = handle_number_game(name, msg)
        if result:
            return jsonify({"reply": result})
    
    # ========== FEATURE #3: PERSONALITY TEST ==========
    if q == "test ya mnyama" or q == "personality test" or q == "mnyama wangu" or q == "test personality":
        reply = start_personality_test(name)
        return jsonify({"reply": reply})
    
    # Handle personality test answers
    if name in user_personality:
        stage = user_personality[name].get('stage', '')
        
        if stage == 'awaiting_answer1':
            if "usiku" in q:
                user_personality[name]['answer1'] = 'usiku'
                reply = personality_test_question2(name)
                return jsonify({"reply": reply})
            elif "mchana" in q:
                user_personality[name]['answer1'] = 'mchana'
                reply = personality_test_question2(name)
                return jsonify({"reply": reply})
            else:
                return jsonify({"reply": "Tafadhali andika 'Usiku' au 'Mchana' 😊"})
        
        elif stage == 'awaiting_answer2':
            if "kuruka" in q:
                user_personality[name]['answer2'] = 'kuruka'
                reply = personality_test_question3(name)
                return jsonify({"reply": reply})
            elif "kuogelea" in q:
                user_personality[name]['answer2'] = 'kuogelea'
                reply = personality_test_question3(name)
                return jsonify({"reply": reply})
            else:
                return jsonify({"reply": "Tafadhali andika 'Kuruka' au 'Kuogelea' 😊"})
        
        elif stage == 'awaiting_answer3':
            if "watu wengi" in q:
                result = process_personality_result(name, 'watu wengi')
                del user_personality[name]
                return jsonify({"reply": result})
            elif "faragha" in q:
                result = process_personality_result(name, 'faragha')
                del user_personality[name]
                return jsonify({"reply": result})
            else:
                return jsonify({"reply": "Tafadhali andika 'Watu wengi' au 'Faragha' 😊"})
    
    # ========== NORMAL CONVERSATION WITH MEMORY ==========
    if name not in conversation_memory:
        conversation_memory[name] = []
    
    # Get last 10 messages for context
    history = "\n".join(conversation_memory[name][-10:])
    
    # Get response from GROQ
    reply = ask_groq(msg, name, history)
    
    # Store in memory
    conversation_memory[name].append(f"Mtumiaji: {msg}")
    conversation_memory[name].append(f"Nexora: {reply}")
    
    # Keep only last 20 messages
    if len(conversation_memory[name]) > 20:
        conversation_memory[name] = conversation_memory[name][-20:]
    
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
