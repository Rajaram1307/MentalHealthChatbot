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
app.secret_key = os.getenv('SECRET_KEY') or 'your_secret_key_here_please_change_it'

# Hardcoded user credentials for demo purposes
DEMO_USERS = {
    "user@example.com": {
        "id": 1,
        "name": "Demo User",
        "password": bcrypt.hashpw(b"password123", bcrypt.gensalt())  # Password is "password123"
    }
}

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
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        
        # Check if user exists in our demo users
        user = DEMO_USERS.get(email)
        
        if user and bcrypt.checkpw(password, user['password']):
            session['user_id'] = user['id']
            session['email'] = email
            session['name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        flash('Registration is disabled in demo mode. Use email: user@example.com and password: password123', 'info')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', 
                             email=session.get('email'),
                             name=session.get('name'))
    else:
        flash('You need to login first', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

# ... [keep all your other routes the same as in your original code] ...

if __name__ == "__main__":
    app.run(debug=True)
