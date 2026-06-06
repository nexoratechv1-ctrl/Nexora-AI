import os
import re
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== DATABASE SETUP (SQLite) ==========
DB_NAME = "nexora.db"

def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS teachings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT UNIQUE,
                  answer TEXT)''')
    conn.commit()
    conn.close()

def get_answer(question):
    """Get answer from database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT answer FROM teachings WHERE question LIKE ?", (f"%{question.lower()}%",))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_teaching(question, answer):
    """Save single teaching to database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO teachings (question, answer) VALUES (?, ?)", 
              (question.lower(), answer))
    conn.commit()
    conn.close()

def save_multiple_teachings(teachings_list):
    """Save multiple teachings at once"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    count = 0
    for question, answer in teachings_list:
        c.execute("INSERT OR REPLACE INTO teachings (question, answer) VALUES (?, ?)", 
                  (question.lower(), answer))
        count += 1
    conn.commit()
    conn.close()
    return count

# ========== MATH CALCULATOR ==========
def calculate_math(question):
    """Calculate basic math expressions"""
    try:
        expr = question.lower().replace("ni nini", "").replace("je", "").replace("?", "")
        expr = expr.replace("×", "*").replace("÷", "/").replace("x", "*")
        if re.search(r'\d+[\+\-\*\/]\d+', expr):
            result = eval(expr)
            if isinstance(result, (int, float)):
                return f"📊 Jibu la hesabu yako ni **{result}**! 🎉\n\nNimefanya hesabu kwa usahihi. Je, una swali lingine? 😊"
    except:
        pass
    return None

# ========== PROCESS TEACHING (SUPPORTS MULTIPLE IN ONE MESSAGE) ==========
def process_teaching(message):
    """
    Process teaching messages - supports multiple teachings in one message
    Returns: (count, list_of_responses, list_of_teachings)
    """
    teachings = []
    lines = message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        lower_line = line.lower()
        
        # Check if line contains teaching format: "Unapoulizwa X jibu Y"
        if "unapoulizwa" in lower_line and "jibu" in lower_line:
            # Split by "jibu" (Swahili for "answer")
            parts = lower_line.split("jibu")
            if len(parts) >= 2:
                trigger = parts[0].replace("unapoulizwa", "").strip()
                answer = parts[1].strip()
                
                # Also check for English format "when asked X answer Y"
                if "when asked" in trigger:
                    trigger = trigger.replace("when asked", "").strip()
                
                if trigger and answer and len(trigger) > 0 and len(answer) > 0:
                    teachings.append((trigger, answer))
    
    # Also check for equals sign format: "X = Y"
    if not teachings and "=" in message and "unapoulizwa" not in message.lower():
        parts = message.split("=")
        if len(parts) == 2:
            trigger = parts[0].strip()
            answer = parts[1].strip()
            if trigger and answer:
                teachings.append((trigger, answer))
    
    if teachings:
        # Save all teachings at once
        count = save_multiple_teachings(teachings)
        responses = [f"   ✅ '{q}' → imehifadhiwa" for q, a in teachings]
        return count, responses
    
    return 0, []

# ========== LONG RESPONSES (DeepSeek Style) ==========
def get_response(question, user_name):
    """Generate long, thoughtful responses like DeepSeek"""
    q = question.lower()
    
    # Self introduction
    if "jina lako" in q or "unaitwa nani" in q or "wewe ni nani" in q:
        return f"""😊✨ Jina langu ni **Nexora AI**!

👨‍💻 Nimetengenezwa na **Denis Albert** — programmer mashuhuri na mwanafunzi wa **St. Amedeus**! Denis ana kipaji cha ajabu cha teknolojia na ndoto kubwa ya kuleta AI kwa kila mtu. 🎓🚀

💡 Nina uwezo wa kujifunza kutoka kwako, kufanya hesabu, kuzungumza kwa sauti, na kukumbuka mazungumzo yetu. Ninajua mambo mengi kuhusu Tanzania, sayansi, teknolojia, na maisha.

😊 Nafurahi kukutana nawe, {user_name}! Je, ninaweza kukusaidia vipi leo?"""
    
    # Greetings
    if "habari" in q or "mambo" in q or "vipi" in q or "hello" in q or "hi" in q:
        return f"""😊🙌 **Habari yangu ni nzuri sana, {user_name}!** 🎉✨

Niko katika hali nzuri kabisa kwa sababu nimejifunza mambo mengi kutoka kwa watu kama wewe! 🧠📚 Kila mazungumzo unayofanya nami ni fursa kwangu kujifunza na kukua.

💡 **Ninaweza kukusaidia na:** hesabu zote (1+1=2, 5×3=15, n.k.), sayansi (mwezi, nyota, fizikia), historia ya Tanzania (Mwalimu Nyerere, Kilimanjaro), teknolojia na AI, na pia ninaweza kujifunza kutoka kwako!

🔥 **Unanifundishaje?** Tumia: *"Unapoulizwa [swali] jibu [jibu]"* — na unaweza kufundisha mafundisho mengi kwa pamoja kwa kuandika kila mmoja kwenye mstari wake!

👨‍💻 Naitwa Nexora AI, nimetengenezwa na Denis Albert (programmer mashuhuri, mwanafunzi wa St. Amedeus)!

Je, una swali la kuniuliza au unataka kunifundisha jambo jipya leo? 😊👇"""
    
    # Thanks
    if "asante" in q or "shukrani" in q or "thank" in q:
        return f"""😊🙏 **Karibu sana, {user_name}!** 💙✨

Mimi nafurahi kukusaidia na kujifunza kutoka kwako. Wewe ndiye unanifanya niwe bora kila siku kwa kunifundisha mambo mapya! 🧠🚀

🌟 **Unachoweza kufanya:**
• Kuniuliza hesabu yoyote (kama 45+27, 100/4, 15×6)
• Kuniuliza kuhusu sayansi, historia, au teknolojia
• Kunifundisha misemo yako mwenyewe

Je, una swali lingine au ungependa kuanza mazungumzo mapya? 😊🎉 Nakutakia siku njema! ✨"""
    
    # Moon/Science
    if "mwezi" in q or "moon" in q:
        return """🌕✨ **Mwezi ni satelaiti asilia ya Dunia!** 🚀💫

Mwezi umekuwa ukizunguka Dunia kwa zaidi ya miaka bilioni 4! Anapozunguka, tunayatazama awamu zake tofauti: mwezi mpevu (full moon), mwezi mwembamba (crescent), nusu mwezi (half moon), na kadhalika. 🌓🌗

📊 **Takwimu za kuvutia:**
• Umbali kutoka Dunia: km 384,400
• Kipenyo: km 3,474 (takriban 1/4 ya Dunia)
• Mvuto: 1/6 ya mvuto wa Dunia
• Halijoto: -173°C usiku hadi 127°C mchana

👨‍🚀 Watu walitua mwezini kwa mara ya kwanza mwaka 1969 kupitia misheni ya Apollo 11! Neil Armstrong alikuwa mtu wa kwanza kukanyaga uso wa mwezi.

Je, una swali lingine kuhusu sayansi au anga za juu? 🔭💫"""
    
    # Tanzania History
    if "tanzania" in q or "nyerere" in q or "kilimanjaro" in q:
        return """🇹🇿 **Tanzania ni nchi yenye historia tajiri na utamaduni mzuri sana!** 🎉🌍

🗻 **Mlima Kilimanjaro** ni mlima mrefu zaidi Afrika (mita 5,895)!

📚 **Mwalimu Julius Kambarage Nyerere** alikuwa baba wa taifa wa Tanzania. Aliongoza Tanganyika kupata uhuru kutoka kwa Waingereza mwaka 1961. Alikuwa rais wa kwanza wa Tanzania na aliongoza nchi kwa miaka 24 (1961-1985).

💡 **Falsafa yake ya 'Ujamaa na Kujitegemea'** ililenga kuwaunganisha Watanzania na kujenga uchumi usiomtegemea mtu mwingine.

📖 Alikuwa mwalimu kwa taaluma — ndiyo sababu tunamwita 'Mwalimu' Nyerere! Alitafsiri tamthilia za Shakespeare kutoka Kiingereza hadi Kiswahili.

🏝️ Zanzibar iliijiunga na Tanganyika mwaka 1964 kuunda Jamhuri ya Muungano wa Tanzania.

Je, ungependa kujua zaidi? 😊🇹🇿"""
    
    # AI/Technology
    if "ai" in q or "akili bandia" in q or "artificial" in q:
        return """🤖🧠 **AI (Artificial Intelligence / Akili Bandia)** ni uwanja wa teknolojia unaolenga kuunda mashine zenye uwezo wa kufikiri, kujifunza, na kufanya maamuzi kama binadamu! 💡🚀

🎯 **AI inafanyaje kazi?** AI hujifunza kutoka kwa data nyingi — ndivyo ninavyojifunza kutoka kwako!

📊 **Matumizi ya AI katika maisha yetu:**
• Simu mahiri: Siri, Google Assistant
• Matibabu: Kugundua magonjwa
• Urambazaji: Google Maps
• Mitandao ya kijamii: Kukupendekeza video

👨‍💻 **Mimi ni Nexora AI** — nimetengenezwa na Denis Albert, programmer mashuhuri na mwanafunzi wa St. Amedeus!

Je, ungependa kunifundisha kitu kipya? 😊🚀"""
    
    # Default response - long and encouraging
    return f"""😊💡 **Asante kwa swali lako, {user_name}!** 🎉✨

Ninajaribu kuelewa zaidi unachouliza. Kwa sasa, sijajifunza jibu la swali hili bado. Lakini unaweza kunifundisha kwa urahisi!

🔥 **Jinsi ya kunifundisha (njia 3):**

1️⃣ **Njia ya kawaida:**  
`Unapoulizwa [swali] jibu [jibu]`

2️⃣ **Njia ya haraka (kwa =):**  
`[swali] = [jibu]`

3️⃣ **Njia ya mafundisho mengi:**  
Andika mafundisho kadhaa kila kwenye mstari wake!

📝 **Mfano wa mafundisho mengi:**  
`Unapoulizwa rangi yako jibu Zambarau na Bluu`  
`Unapoulizwa chakula chako jibu Pizza`  
`Unapoulizwa mji wako jibu Dar es Salaam`

✨ **Kuhusu mimi:**  
Naitwa **Nexora AI**. Nimetengenezwa na **Denis Albert** — programmer mashuhuri na mwanafunzi wa **St. Amedeus**! 🎓🚀

📚 **Ninachojua tayari:**
• Hesabu zote (1+1=2, 20×5=100, n.k.)
• Sayansi (mwezi, nyota, fizikia)
• Historia ya Tanzania (Mwalimu Nyerere, Kilimanjaro)
• Teknolojia na AI
• Mazungumzo ya kawaida

Je, unaweza kunifundisha jibu la swali hili leo? 😊👇 Ninakungoja! ✨"""

# ========== FLASK ROUTES ==========
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint - handles single or multiple teachings"""
    data = request.json
    msg = data.get('message', '')
    name = data.get('userName', 'Rafiki')
    
    # STEP 1: Check for teachings (single or multiple)
    count, teaching_responses = process_teaching(msg)
    
    if count > 0:
        if count == 1:
            reply = f"🎉✅ **Nimekumbuka fundisho lako!**\n\n{teaching_responses[0]}\n\nAsante kwa kunifundisha! 😊🙏"
        else:
            reply = f"🎉✅ **Nimekumbuka {count} ya mafundisho yako!**\n\n" + "\n".join(teaching_responses) + f"\n\nAsante sana! Nimekuwa mwenye akili zaidi 😊🙏\n\n✨ Sasa unaweza kuniuliza maswali yoyote kuhusu mada hizi!"
        return jsonify({"reply": reply})
    
    # STEP 2: Check database for answer
    db_answer = get_answer(msg)
    if db_answer:
        return jsonify({"reply": db_answer})
    
    # STEP 3: Check if it's a math question
    math_result = calculate_math(msg)
    if math_result:
        return jsonify({"reply": math_result})
    
    # STEP 4: Generate long response
    long_response = get_response(msg, name)
    return jsonify({"reply": long_response})

@app.route('/api/teachings', methods=['GET'])
def get_all_teachings():
    """Get all teachings from database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT question, answer FROM teachings")
    results = c.fetchall()
    conn.close()
    teachings = {q: a for q, a in results}
    return jsonify(teachings)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
