from flask import Flask, request, jsonify, render_template
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rajaram001'
app.config['MYSQL_DB'] = 'journal'

mysql = MySQL(app)

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
    mood = data.get('mood')
    content = data.get('content')
    username = "guest_user"  # Replace with actual user handling if needed

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

        # Format the timestamp as ISO string to avoid "Invalid Date" in JS
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

# ---------------- MAIN ----------------

if __name__ == '__main__':
    app.run(debug=True)
