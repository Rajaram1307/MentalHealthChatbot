from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# SQLite Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journals.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Journal Model
class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50))
    content = db.Column(db.Text)
    username = db.Column(db.String(50), default="guest_user")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/main')
def main_page():
    return render_template('main.html')

@app.route('/create_journal.html')
def create_journal_page():
    return render_template('create_journal.html')

@app.route('/edit_journal.html')
def edit_journal_page():
    return render_template('edit_journal.html')

# ---------------- API ROUTES ----------------
@app.route('/api/journals', methods=['POST'])
def create_journal():
    data = request.json
    if not data or 'mood' not in data or 'content' not in data:
        return jsonify({'error': 'Mood and content are required'}), 400
    
    new_journal = Journal(
        mood=data['mood'],
        content=data['content']
    )
    db.session.add(new_journal)
    db.session.commit()
    return jsonify({'message': 'Journal created successfully'}), 201

@app.route('/api/journals', methods=['GET'])
def get_journals():
    journals = Journal.query.filter_by(username="guest_user").order_by(Journal.timestamp.desc()).all()
    journals_data = [{
        'id': journal.id,
        'mood': journal.mood,
        'content': journal.content,
        'timestamp': journal.timestamp.isoformat()
    } for journal in journals]
    return jsonify(journals_data), 200

@app.route('/api/journals/<int:id>', methods=['GET'])
def get_journal(id):
    journal = Journal.query.filter_by(id=id, username="guest_user").first()
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    
    return jsonify({
        'id': journal.id,
        'mood': journal.mood,
        'content': journal.content,
        'timestamp': journal.timestamp.isoformat()
    }), 200

@app.route('/api/journals/<int:id>', methods=['PUT'])
def update_journal(id):
    journal = Journal.query.filter_by(id=id, username="guest_user").first()
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    
    data = request.json
    if 'mood' in data:
        journal.mood = data['mood']
    if 'content' in data:
        journal.content = data['content']
    
    db.session.commit()
    return jsonify({'message': 'Journal updated successfully'}), 200

@app.route('/api/journals/<int:id>', methods=['DELETE'])
def delete_journal(id):
    journal = Journal.query.filter_by(id=id, username="guest_user").first()
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    
    db.session.delete(journal)
    db.session.commit()
    return jsonify({'message': 'Journal deleted successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
