from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "smart_clothesline_db")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "secret_key_secure")

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME, autocommit=True, connect_timeout=5
        )
        return conn
    except Error as e:
        print(f"Database error: {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Anda harus login terlebih dahulu", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_control_exists(user_id):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM control WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO control (user_id, current_control_mode, current_manual_command) VALUES (%s, 'AUTO', 'IDLE')", (user_id,))
            conn.commit()
        conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        if not conn:
            flash("Database error", "error")
            return redirect(url_for('index'))
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                ensure_control_exists(user['id'])
                flash("Login berhasil!", "success")
                return redirect(url_for('home'))
            else:
                flash("Username atau password salah", "error")
        finally:
            if conn: conn.close()
        return render_template('index.html')
    return render_template('index.html')

@app.route('/home')
@login_required
def home():
    rows = []
    current_status = {}
    control_state = {}
    
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            user_id = session['user_id']
            
            cur.execute("SELECT current_control_mode, current_manual_command FROM control WHERE user_id = %s", (user_id,))
            control_state = cur.fetchone() or {'current_control_mode': 'AUTO'}

            cur.execute("SELECT waktu as waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data WHERE user_id = %s ORDER BY waktu DESC LIMIT 50", (user_id,))
            rows = cur.fetchall()
            
            cur.execute("SELECT temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data WHERE user_id = %s ORDER BY waktu DESC LIMIT 1", (user_id,))
            current_status = cur.fetchone() or {}
        finally:
            conn.close()
    
    # Init render variables
    db_mode = control_state.get('current_control_mode', 'AUTO')
    control_mode = 'AUTO'
    system_on = False

    if db_mode == 'MANUAL':
        control_mode = 'MANUAL'
        system_on = True 
    elif db_mode == 'OFF':
        control_mode = 'AUTO' # Di HTML tetap render mode, tapi system_on False
        system_on = False
    else: # AUTO
        control_mode = 'AUTO'
        system_on = True

    return render_template(
        "home.html",
        table_rows=rows,
        system_on=system_on,
        control_mode=control_mode,
        username=session['username'],
        current_status=current_status,
        datetime=datetime
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah berhasil logout", "success")
    return redirect(url_for('index'))

@app.route("/set_mode", methods=["POST"])
@login_required
def set_mode():
    try:
        payload = request.get_json()
        new_mode = payload.get("mode") # AUTO, MANUAL, OFF
        user_id = session['user_id']
        
        valid_modes = ["AUTO", "MANUAL", "OFF"]
        
        if new_mode in valid_modes:
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                
                if new_mode == "OFF":
                    # Logic: Set Mode=AUTO but status=OFF (di tabel users) atau pakai flag khusus
                    # Disini saya simpan "OFF" ke current_control_mode agar konsisten
                    cur.execute("UPDATE control SET current_control_mode = 'OFF' WHERE user_id = %s", (user_id,))
                else:
                    cur.execute("UPDATE control SET current_control_mode = %s WHERE user_id = %s", (new_mode, user_id))
                
                conn.commit()
                conn.close()
                return jsonify({"message": "Mode updated", "mode": new_mode})
        return jsonify({"error": "Invalid mode"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/manual_control", methods=["POST"])
@login_required
def manual_control():
    try:
        payload = request.get_json()
        command = payload.get("command")
        user_id = session['user_id']

        if command in ["OPEN", "CLOSE"]:
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("UPDATE control SET current_manual_command = %s WHERE user_id = %s", (command, user_id))
                conn.commit()
                conn.close()
                return jsonify({"message": "Command sent", "command": command})
        return jsonify({"error": "Invalid command"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/system_status")
def get_system_status():
    target_user = request.args.get('username')
    conn = get_connection()
    status_data = {"status": "OFF", "mode": "AUTO", "manual_cmd": "IDLE"}
    
    if conn and target_user:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE username = %s", (target_user,))
            user = cur.fetchone()
            
            if user:
                cur.execute("SELECT current_control_mode, current_manual_command FROM control WHERE user_id = %s", (user['id'],))
                ctrl = cur.fetchone()
                
                if ctrl:
                    db_mode = ctrl['current_control_mode']
                    
                    if db_mode == 'OFF':
                        status_data["status"] = "OFF"
                        status_data["mode"] = "AUTO" # Arduino logic: if auto & off = idle
                    elif db_mode == 'MANUAL':
                        status_data["status"] = "ON" # Manual but active control
                        status_data["mode"] = "MANUAL"
                    else: # AUTO
                        status_data["status"] = "ON"
                        status_data["mode"] = "AUTO"
                        
                    status_data["manual_cmd"] = ctrl['current_manual_command']
        finally:
            conn.close()

    return jsonify(status_data)

@app.route("/data")
@login_required
def get_data():
    conn = get_connection()
    if not conn: return jsonify({"error": "DB Connection Failed"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        user_id = session['user_id']
        
        cur.execute("SELECT current_control_mode FROM control WHERE user_id = %s", (user_id,))
        control_state = cur.fetchone() or {'current_control_mode': 'AUTO'}
        
        cur.execute("SELECT waktu as waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data WHERE user_id = %s ORDER BY waktu DESC LIMIT 1", (user_id,))
        latest = cur.fetchone()
        
        cur.execute("SELECT waktu as waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data WHERE user_id = %s ORDER BY waktu DESC LIMIT 50", (user_id,))
        history = cur.fetchall()
        conn.close()
        
        db_mode = control_state['current_control_mode']
        
        ui_system_on = True
        ui_mode = "AUTO"

        if db_mode == 'OFF':
            ui_system_on = False
            ui_mode = "AUTO" # Supaya JS logic render OFF
        elif db_mode == 'MANUAL':
            ui_system_on = True
            ui_mode = "MANUAL"
        else:
            ui_system_on = True
            ui_mode = "AUTO"

        return jsonify({
            "latest": latest,
            "history": history,
            "flask_system_status": "OFF" if db_mode == 'OFF' else "ON",
            "control_mode": 'AUTO' if db_mode == 'OFF' else db_mode
        })
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route("/insert", methods=["POST"])
def insert_data():
    try:
        payload = request.get_json(force=True)
        username = payload.get("username")
        
        if not username: return jsonify({"error": "Username required"}), 400

        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_res = cur.fetchone()
            
            if user_res:
                user_id = user_res[0]
                sql = """INSERT INTO jemuran_data 
                         (user_id, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cur.execute(sql, (
                    user_id,
                    float(payload.get("temperature")), 
                    float(payload.get("humidity")), 
                    int(payload.get("rain_value")), 
                    int(payload.get("ldr_value")), 
                    payload.get("status_jemuran"), 
                    payload.get("status_system")
                ))
                conn.commit()
                conn.close()
                return jsonify({"message": "Data saved"})
            else:
                conn.close()
                return jsonify({"error": "User not found"}), 404
        return jsonify({"error": "DB Error"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)