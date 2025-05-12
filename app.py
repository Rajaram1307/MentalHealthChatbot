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

# Initialize Flask App with SQLite
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mentalhealth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()
    # Create demo user if none exists
    if not User.query.first():
        demo_user = User(
            name="Demo User",
            email="user@example.com",
            password=bcrypt.hashpw(b"password123", bcrypt.gensalt())
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
                "Keep response brief (1-2 sentences), supportive."
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
    return "I'm here for you. How can I assist you today?"

# Authentication Routes
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
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
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
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists', 'error')
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html', 
                         name=session.get('name'),
                         email=session.get('email'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

# Application Modules (with original template names)
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')  # Original template name

@app.route('/food')
def food():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('food.html')  # Original template name

@app.route('/main')
def journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('main.html')  # Original template name

@app.route('/create_journal')
def create_journal_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('create_journal.html')  # Original template name

@app.route('/medi')
def meditation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('medi.html')  # Original template name

@app.route('/quizz')
def quizz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('quizz.html')  # Original template name

@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('stats.html')  # Original template name

@app.route('/resources')
def resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('resources.html')  # Original template name

@app.route('/blogindex')
def blog_index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('blogindex.html', posts=posts)  # Original template name

# API Endpoints
@app.route('/api/journals', methods=['POST'])
def create_journal():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    journal = Journal(
        user_id=session['user_id'],
        mood=data.get('mood'),
        content=data.get('content')
    )
    db.session.add(journal)
    db.session.commit()
    return jsonify({'message': 'Journal created successfully'}), 201

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

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    post = Post(
        user_id=session['user_id'],
        title=request.form['title'],
        content=request.form['content']
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('blog_index'))

# AI Endpoints
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
        return jsonify({"mood": analysis['dominant_emotion']})
    except Exception as e:
        return jsonify({"mood": "no_face", "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
