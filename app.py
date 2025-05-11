from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
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

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rajaram001'
app.config['MYSQL_DB'] = 'final'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.secret_key = 'your_secret_key'

mysql = MySQL(app)

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
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        cursor = mysql.connection.cursor()

        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                           (name, email, hashed_password))
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Email already exists or an error occurred.', 'error')
        finally:
            cursor.close()

    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', email=session['email'])
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()
    cursor.close()
    return render_template('blogindex.html', posts=posts)

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO posts (title, content) VALUES (%s, %s)", (title, content))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('blog_index'))
    return render_template('create_post.html')

@app.route('/like/<int:post_id>')
def like_post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id = %s", (post_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('blog_index'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if not post:
        flash("Post not found!", "error")
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM comments WHERE post_id = %s ORDER BY created_at DESC", (post_id,))
    comments = cursor.fetchall()
    cursor.close()

    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    comment = request.form['comment']
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("INSERT INTO comments (post_id, comment) VALUES (%s, %s)", (post_id, comment))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error adding comment: {e}', 'error')
    finally:
        cursor.close()
    return redirect(url_for('post_detail', post_id=post_id))

# ---------------- JOURNAL API ROUTES ----------------

@app.route('/api/journals', methods=['POST'])
def create_journal():
    data = request.json
    mood = data.get('mood')
    content = data.get('content')
    username = "guest_user"

    if not mood or not content:
        return jsonify({'error': 'All fields are required'}), 400

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO journal (mood, content, username, timestamp) VALUES (%s, %s, %s, %s)",
                       (mood, content, username, datetime.now()))
        mysql.connection.commit()
        return jsonify({'message': 'Journal created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/api/journals', methods=['GET'])
def get_journals():
    username = "guest_user"
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM journal WHERE username = %s ORDER BY timestamp DESC", (username,))
        journals = cursor.fetchall()
        for journal in journals:
            if isinstance(journal['timestamp'], datetime):
                journal['timestamp'] = journal['timestamp'].isoformat()
        return jsonify(journals), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/api/journals/<int:id>', methods=['GET'])
def get_journal(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM journal WHERE id = %s", (id,))
    journal = cursor.fetchone()
    cursor.close()

    if journal and journal['username'] == "guest_user":
        if isinstance(journal['timestamp'], datetime):
            journal['timestamp'] = journal['timestamp'].isoformat()
        return jsonify(journal), 200
    return jsonify({'error': 'Journal not found or access denied'}), 404

@app.route('/api/journals/<int:id>', methods=['PUT'])
def update_journal(id):
    data = request.json
    mood = data.get('mood')
    content = data.get('content')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM journal WHERE id = %s", (id,))
    journal = cursor.fetchone()

    if not journal or journal['username'] != "guest_user":
        return jsonify({'error': 'Access denied'}), 403

    try:
        cursor.execute("UPDATE journal SET mood = %s, content = %s WHERE id = %s", (mood, content, id))
        mysql.connection.commit()
        return jsonify({'message': 'Journal updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

@app.route('/api/journals/<int:id>', methods=['DELETE'])
def delete_journal(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM journal WHERE id = %s", (id,))
    journal = cursor.fetchone()

    if not journal or journal['username'] != "guest_user":
        return jsonify({'error': 'Access denied'}), 403

    try:
        cursor.execute("DELETE FROM journal WHERE id = %s", (id,))
        mysql.connection.commit()
        return jsonify({'message': 'Journal deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

if __name__ == "__main__":
    app.run(debug=True)