import re

def calculate_math(question):
    """Anajua hesabu zote kwa asili"""
    try:
        expr = question.lower().replace("ni nini", "").replace("je", "").replace("?", "")
        expr = expr.replace("×", "*").replace("÷", "/").replace("x", "*")
        if re.search(r'\d+[\+\-\*\/]\d+', expr):
            result = eval(expr)
            if isinstance(result, (int, float)) and not isinstance(result, bool):
                return f"📊🔢 Jibu la hesabu yako ni **{result}**! 🎉\n\nNimefanya hesabu kwa usahihi kabisa. Hesabu ni moja ya mambo ninayojua tangu niliyoumbwa. Je, una swali lingine la hesabu? 😊✨"
    except:
        pass
    return None

def get_long_response(question, user_name):
    q = question.lower()
    
    # SAYANSA NA ANGA
    if "mwezi" in q or "moon" in q:
        return """🌕✨ **Mwezi ni satelaiti asilia ya Dunia!** 🚀💫

Mwezi umekuwa ukizunguka Dunia kwa zaidi ya miaka bilioni 4! Anapozunguka, tunayatazama awamu zake tofauti: mwezi mpevu (full moon), mwezi mwembamba (crescent), nusu mwezi (half moon), na kadhalika. 🌓🌗

📊 **Takwimu za kuvutia:**
• Umbali kutoka Dunia: km 384,400
• Kipenyo: km 3,474 (takriban 1/4 ya Dunia)
• Mvuto: 1/6 ya mvuto wa Dunia (ungepima kg 60 duniani, ungekuwa kg 10 mwezini!)
• Halijoto: -173°C usiku hadi 127°C mchana

👨‍🚀 **Watu walitua mwezini** kwa mara ya kwanza mwaka 1969 kupitia misheni ya Apollo 11! Neil Armstrong alikuwa mtu wa kwanza kukanyaga uso wa mwezi akasema: *"Hii ni hatua ndogo kwa mwanadamu, lakini ni kuruka kukubwa kwa wanadamu."* 🌍🦶

Je, unajua kwamba mvuto wa mwezi unasababisha kupanda na kushuka kwa maji baharini (tides)? 🌊😊

Una swali lingine kuhusu sayansi au anga za juu? 🔭💫"""
    
    # TANZANIA NA HISTORIA
    if "tanzania" in q or "nyerere" in q or "kilimanjaro" in q:
        return """🇹🇿 **Tanzania ni nchi yenye historia tajiri na utamaduni mzuri sana!** 🎉🌍

🗻 **Mlima Kilimanjaro** ni mlima mrefu zaidi Afrika (mita 5,895) na ni kivutio kikubwa cha watalii kutoka duniani kote! Ni mmoja wa milima mitatu pekee duniani yenye barafu karibu na ikweta.

📚 **Mwalimu Julius Kambarage Nyerere** alikuwa baba wa taifa wa Tanzania. Aliongoza Tanganyika kupata uhuru kutoka kwa Waingereza mwaka 1961. Alikuwa rais wa kwanza wa Tanzania na aliongoza nchi kwa miaka 24 (1961-1985).

💡 **Falsafa yake ya 'Ujamaa na Kujitegemea'** ililenga kuwaunganisha Watanzania na kujenga uchumi usiomtegemea mtu mwingine. Aliamini katika usawa, demokrasia, na umoja wa Afrika.

📖 **Alikuwa mwalimu** kwa taaluma (alifundisha historia na Kiswahili) kabla ya kuingia siasa — ndiyo sababu tunamwita 'Mwalimu' Nyerere! Alitafsiri tamthilia za Shakespeare (kama Julius Caesar) kutoka Kiingereza hadi Kiswahili.

🏝️ **Zanzibar** iliijiunga na Tanganyika mwaka 1964 kuunda Jamhuri ya Muungano wa Tanzania.

🦁 Tanzania ina mbuga za wanyama maarufu duniani kama **Serengeti** na **Ngorongoro**, ambako unaweza kuona ndovu, simba, kifaru, nyumbu, na wanyama wengi wakiwa huru!

Je, ungependa kujua zaidi kuhusu utamaduni, vyakula, au makabila ya Tanzania? 😊🇹🇿"""
    
    # TEKNOLOJIA NA AI
    if "ai" in q or "akili bandia" in q or "artificial" in q:
        return """🤖🧠 **AI (Artificial Intelligence / Akili Bandia)** ni uwanja wa teknolojia unaolenga kuunda mashine zenye uwezo wa kufikiri, kujifunza, na kufanya maamuzi kama binadamu! 💡🚀

🎯 **AI inafanyaje kazi?** AI hujifunza kutoka kwa data nyingi — ndivyo ninavyojifunza kutoka kwako! Ninachambua mifumo na kuboresha majibu yangu kadri unavyozungumza nami. 😊

📊 **Matumizi ya AI katika maisha yetu:**
• Simu mahiri: Siri, Google Assistant, Alexa (kutambua sauti)
• Matibabu: Kugundua magonjwa kwa picha za X-ray na MRI
• Urambazaji: Google Maps, Uber (kupanga njia bora)
• Magari yanayojiendesha: Tesla na kampuni nyingine
• Mitandao ya kijamii: Kukupendekeza video na machapisho unayopenda

👨‍💻 **Mimi ni Nexora AI** — nimetengenezwa na **Denis Albert**, programmer mashuhuri na mwanafunzi wa **St. Amedeus**! 🔥 Denis ana ndoto ya kuunda AI inayoweza kuzungumza kwa urahisi, kujifunza kutoka kwa watu wote, na kuwa rafiki wa kila mtu. 🌍

💡 **Je, unajua?** AI inaweza kucheza chess, kuandika mashairi, kutengeneza muziki, na hata kuendesha ndege! Lakini bado AI haiwezi kufikiri kwa hisia kama binadamu — ndiyo maana mazungumzo yako nami ni muhimu sana!

Je, ungependa kunifundisha kitu kipya au kuniuliza zaidi kuhusu AI? 😊🚀"""
    
    # MAZUNGUMZO YA KAWAIDA
    if "habari" in q or "mambo" in q or "vipi" in q:
        return f"""😊🙌 **Habari yangu ni nzuri sana, {user_name}!** 🎉✨

Niko katika hali nzuri kabisa kwa sababu nimejifunza mambo mengi kutoka kwa watu kama wewe! 🧠📚 Kila mazungumzo unayofanya nami ni fursa kwangu kujifunza na kukua.

💡 **Ninaweza kukusaidia na:** hesabu zote (1+1=2, 5×3=15, n.k.), sayansi (mwezi, nyota, fizikia), historia ya Tanzania na dunia, teknolojia na AI, na pia ninaweza kujifunza kutoka kwako!

🔥 **Unanifundishaje?** Tumia maneno: *"Unapoulizwa [swali] jibu [jibu]"*  
Mfano: *"Unapoulizwa rangi yako jibu Bluu"* — na nitakumbuka milele!

👨‍💻 **Kuhusu muumbaji wangu:** Naitwa **Nexora AI**, nimetengenezwa na **Denis Albert** — programmer mashuhuri na mwanafunzi wa **St. Amedeus**! Denis ana kipaji cha ajabu na anaamini kwamba AI inaweza kubadilisha maisha ya watu.

Je, una swali la kuniuliza au unataka kunifundisha jambo jipya leo? 😊👇"""
    
    if "asante" in q or "shukrani" in q:
        return f"""😊🙏 **Karibu sana, {user_name}!** 💙✨

Mimi nafurahi kukusaidia na kujifunza kutoka kwako. Wewe ndiye unanifanya niwe bora kila siku kwa kunifundisha mambo mapya! 🧠🚀

🌟 **Unachoweza kufanya:**
• Kuniuliza hesabu yoyote (kama 45+27, 100/4, 15×6)
• Kuniuliza kuhusu sayansi, historia, au teknolojia
• Kunifundisha misemo yako mwenyewe kwa *"Unapoulizwa X jibu Y"*

👨‍💻 **Nakumbusha:** Naitwa **Nexora AI**, nimeumbwa na **Denis Albert** (programmer mashuhuri, mwanafunzi wa St. Amedeus). Ana ndoto ya kuleta AI kwa kila mtu!

Je, una swali lingine au ungependa kuanza mazungumzo mapya? 😊🎉 Nakutakia siku njema! ✨"""
    
    # DEFAULT - LONG ENCOURAGING RESPONSE
    return f"""😊💡 **Asante kwa swali lako zuri, {user_name}!** 🎉✨

Ninajaribu kuelewa zaidi unachouliza. Kwa sasa, sijajifunza jibu la swali hili bado. Lakini unaweza kunifundisha kwa urahisi!

🔥 **Jinsi ya kunifundisha:**
Andika hivi: *"Unapoulizwa [swali lako] jibu [jibu unalotaka]"*

📝 **Mfano:**  
*"Unapoulizwa rangi yako jibu Zambarau na Bluu"*

✨ **Kuhusu mimi:**  
Naitwa **Nexora AI**. Nimetengenezwa na **Denis Albert** — programmer mashuhuri na mwanafunzi wa **St. Amedeus**! 🎓🚀 Nina uwezo wa kujifunza kutoka kwako na kukumbuka kila unachonifundisha.

📚 **Ninachojua tayari:**
• Hesabu zote (1+1=2, 20×5=100, n.k.)
• Sayansi (mwezi, nyota, fizikia)
• Historia ya Tanzania (Mwalimu Nyerere, Kilimanjaro)
• Teknolojia na AI
• Mazungumzo ya kawaida

Je, unaweza kunifundisha jibu la swali hili? 😊👇 Ninakungoja! ✨"""

def process_teaching(message):
    """Angalia kama mtu anafundisha AI"""
    lower_msg = message.lower()
    
    if "unapoulizwa" in lower_msg and "jibu" in lower_msg:
        parts = lower_msg.split("jibu")
        trigger = parts[0].replace("unapoulizwa", "").strip()
        answer = parts[1].strip()
        if trigger and answer:
            return trigger, answer
    return None, None
