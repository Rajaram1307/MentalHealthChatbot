from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
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

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyCzgAFXz01xdHcTEHbNb0zd5hyK3jA0gdQ')
genai.configure(api_key=GEMINI_API_KEY)
try:
    gemini_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Error initializing Gemini: {e}")
    gemini_model = None

# Initialize Flask App
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()
    # Create demo user if not exists
    if not User.query.filter_by(email="user@example.com").first():
        hashed_pw = bcrypt.hashpw(b"password123", bcrypt.gensalt())
        demo_user = User(
            name="Demo User",
            email="user@example.com",
            password=hashed_pw
        )
        db.session.add(demo_user)
        db.session.commit()

# Helper Functions
def classify_intent(user_text):
    with open('intents.json') as json_data:
        intents = json.load(json_data)
    
    for intent in intents['intents']:
        for pattern in intent['patterns']:
            if re.search(r'\b' + re.escape(pattern) + r'\b', user_text, re.IGNORECASE):
                return random.choice(intent['responses'])
    
    if gemini_model:
        try:
            response = gemini_model.generate_content(
                f"Mental health support response to: {user_text}\n"
                "Keep it brief (1-2 sentences), empathetic, and supportive."
            )
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")
    
    return "I'm here for you. How can I help today?"

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.checkpw(password, user.password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            hashed_pw = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            user = User(
                name=request.form['name'],
                email=request.form['email'],
                password=hashed_pw
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists', 'error')
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', email=session['email'])

# Chat Module
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/get', methods=['POST'])
def chatbot_response():
    user_text = request.form['msg']
    return str(classify_intent(user_text))

# Journal Module
@app.route('/journal')
def journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('main.html')

@app.route('/create_journal')
def create_journal_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('create_journal.html')

@app.route('/api/journals', methods=['POST'])
def create_journal():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    journal = Journal(
        mood=data['mood'],
        content=data['content'],
        user_id=session['user_id']
    )
    db.session.add(journal)
    db.session.commit()
    return jsonify({'message': 'Journal saved'}), 201

@app.route('/api/journals', methods=['GET'])
def get_journals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    journals = Journal.query.filter_by(user_id=session['user_id']).order_by(Journal.timestamp.desc()).all()
    return jsonify([{
        'id': j.id,
        'mood': j.mood,
        'content': j.content,
        'timestamp': j.timestamp.isoformat()
    } for j in journals])

# Blog Module
@app.route('/blog')
def blog_index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('blogindex.html', posts=posts)

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    post = Post(
        title=request.form['title'],
        content=request.form['content'],
        user_id=session['user_id']
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('blog_index'))

# Meditation Module
@app.route('/meditation')
def meditation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('medi.html')

# Quiz Module
@app.route('/quiz')
def quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('quizz.html')

# Stats Module
@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('stats.html')

# Resources Module
@app.route('/resources')
def resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('resources.html')

# Food Module
@app.route('/food')
def food():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('food.html')

# Emotion Analysis Module
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

@app.route('/start-capture')
def start_capture():
    user_mood = capture_emotions()
    return jsonify({"mood": user_mood})

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

    cap.release()
    cv2.destroyAllWindows()

    if captured_expressions:
        final_emotion = Counter(captured_expressions).most_common(1)[0][0]
    else:
        final_emotion = "No emotion detected"

    return final_emotion

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
