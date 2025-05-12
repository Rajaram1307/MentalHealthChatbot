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

# Journal Endpoints
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

# Blog Endpoints
@app.route('/blogindex.html')
def blog_index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('blogindex.html', posts=posts)

@app.route('/create', methods=['POST'])
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

# ... [Keep all your other existing routes like /analyze-image, /chat, etc.] ...

if __name__ == '__main__':
    app.run(debug=True)
