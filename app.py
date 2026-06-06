from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from database import get_answer, save_teaching, get_all_teachings
from ai_responses import calculate_math, get_long_response, process_teaching

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    user_name = data.get('userName', 'Rafiki')
    
    # Kwanza, angalia kama anafundisha
    trigger, answer = process_teaching(user_message)
    if trigger and answer:
        save_teaching(trigger, answer)
        return jsonify({
            "reply": f"🎉 **Nimekumbuka!** ✨\n\nSasa unapoulizwa \"{trigger}\", nitajibu: \"{answer}\"\n\nAsante kwa kunifundisha! Umenifanya niwe mwenye akili zaidi. 😊💡"
        })
    
    # Angalia kama swali lina jibu kwenye database
    db_answer = get_answer(user_message)
    if db_answer:
        return jsonify({"reply": db_answer})
    
    # Angalia kama ni hesabu
    math_result = calculate_math(user_message)
    if math_result:
        return jsonify({"reply": math_result})
    
    # Toa jibu refu kama DeepSeek
    long_response = get_long_response(user_message, user_name)
    return jsonify({"reply": long_response})

@app.route('/api/teachings', methods=['GET'])
def get_teachings():
    teachings = get_all_teachings()
    return jsonify(teachings)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
