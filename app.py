from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import bcrypt
from deepface import DeepFace
from collections import Counter
from datetime import datetime
import cv2
import numpy as np
import json
import random
import re
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure Gemini API with proper model name
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or 'AIzaSyCzgAFXz01xdHcTEHbNb0zd5hyK3jA0gdQ'
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the correct model name
try:
    # Try the most recent model names
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception as e:
    print(f"Error with gemini-1.5-pro-latest: {e}")
    try:
        gemini_model = genai.GenerativeModel('gemini-pro')
    except Exception as fallback_e:
        print(f"Error with gemini-pro: {fallback_e}")
        gemini_model = None

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'

# Load intents
with open('intents.json') as json_data:
    intents = json.load(json_data)

def classify_intent(user_text):
    # First try to match with local intents
    for intent in intents['intents']:
        for pattern in intent['patterns']:
            if re.search(r'\b' + re.escape(pattern) + r'\b', user_text, re.IGNORECASE):
                return random.choice(intent['responses'])
    
    # If no local match and Gemini is configured, use Gemini API
    if gemini_model:
        try:
            response = gemini_model.generate_content(
                f"You are a mental health support chatbot. Provide a helpful, empathetic response to: {user_text}\n"
                "Keep response brief (1-2 sentences), supportive, and mental health focused.\n"
                "For serious concerns, suggest professional help."
            )
            return response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
    
    return "I'm here for you. How can I assist you today?"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        flash('Login functionality is currently disabled', 'error')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        flash('Registration functionality is currently disabled', 'error')
        return redirect(url_for('register'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', email=session.get('email', 'guest@example.com'))
    else:
        flash('You need to login first', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

@app.route('/chat.html')
def chat():
    return render_template('chat.html')

@app.route('/main.html')
def journal():
    return render_template('main.html')

@app.route('/create_journal.html')
def create_journal_page():
    return render_template('create_journal.html')

@app.route('/edit_journal.html')
def edit_journal_page():
    return render_template('edit_journal.html')

@app.route('/medi.html')
def medi():
    return render_template('medi.html')

@app.route('/quizz.html')
def quiz():
    return render_template('quizz.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/food.html')
def food():
    return render_template('food.html')

@app.route('/get', methods=['POST'])
def chatbot_response():
    user_text = request.form['msg']
    return str(classify_intent(user_text))

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    file = request.files['image']
    npimg = np.fromfile(file, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    try:
        analysis = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)
        dominant_emotion = analysis['dominant_emotion']
        return jsonify({"mood": dominant_emotion})
    except ValueError as e:
        return jsonify({"mood": "no_face", "error": str(e)})

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def capture_emotions():
    cap = cv2.VideoCapture(0)
    captured_expressions = []
    capture_limit = 20

    while len(captured_expressions) < capture_limit:
        ret, frame = cap.read()
        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb_frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2RGB)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face_roi = rgb_frame[y:y + h, x:x + w]
            result = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
            emotion = result[0]['dominant_emotion']
            if emotion == "neutral":
                emotion = "sad"
            captured_expressions.append(emotion)

        cv2.imshow('Capturing Emotion...', frame)
        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()

    if captured_expressions:
        final_emotion = Counter(captured_expressions).most_common(1)[0][0]
    else:
        final_emotion = "No emotion detected"

    return final_emotion

@app.route('/start-capture')
def start_capture():
    user_mood = capture_emotions()
    return jsonify({"mood": user_mood})

# ------------------- BLOG MODULE ------------------

@app.route('/blogindex.html',endpoint='index')
def blog_index():
    # Return empty list since we removed database functionality
    return render_template('blogindex.html', posts=[])

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        flash('Blog functionality is currently disabled', 'error')
        return redirect(url_for('blog_index'))
    return render_template('create_post.html')

@app.route('/like/<int:post_id>')
def like_post(post_id):
    flash('Blog functionality is currently disabled', 'error')
    return redirect(url_for('blog_index'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    flash('Blog functionality is currently disabled', 'error')
    return redirect(url_for('blog_index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    flash('Blog functionality is currently disabled', 'error')
    return redirect(url_for('blog_index'))

# ---------------- JOURNAL API ROUTES ----------------

@app.route('/api/journals', methods=['POST'])
def create_journal():
    return jsonify({'error': 'Journal functionality is currently disabled'}), 503

@app.route('/api/journals', methods=['GET'])
def get_journals():
    return jsonify({'error': 'Journal functionality is currently disabled'}), 503

@app.route('/api/journals/<int:id>', methods=['GET'])
def get_journal(id):
    return jsonify({'error': 'Journal functionality is currently disabled'}), 503

@app.route('/api/journals/<int:id>', methods=['PUT'])
def update_journal(id):
    return jsonify({'error': 'Journal functionality is currently disabled'}), 503

@app.route('/api/journals/<int:id>', methods=['DELETE'])
def delete_journal(id):
    return jsonify({'error': 'Journal functionality is currently disabled'}), 503

if __name__ == "__main__":
    app.run(debug=True)
