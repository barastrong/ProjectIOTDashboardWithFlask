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
app.secret_key = os.getenv("SECRET_KEY", "ganti-dengan-kunci-rahasia-yang-unik-dan-kuat")

system_on = False
rain_status_from_hp = "NO_RAIN"

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME, autocommit=True, connect_timeout=5
        )
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Anda harus login terlebih dahulu", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        if not conn:
            flash("Tidak dapat terhubung ke database. Silakan coba lagi nanti.", "error")
            return redirect(url_for('index'))
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash("Login berhasil!", "success")
                return redirect(url_for('home'))
            else:
                flash("Username atau password salah", "error")
        except Error as e:
            flash(f"Terjadi kesalahan pada database: {e}", "error")
        finally:
            if 'cur' in locals() and cur:
                cur.close()
            if conn:
                conn.close()
        return render_template('index.html')
    return render_template('index.html')

@app.route('/home')
@login_required
def home():
    rows = []
    current_status = {}
    conn = get_connection()
    if not conn:
        flash("Gagal terhubung ke database untuk memuat data.", "error")
    else:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 100")
            rows = cur.fetchall()
            cur.execute("SELECT temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 1")
            current_status = cur.fetchone() or {}
        except Error as e:
            flash(f"Gagal memuat data: {e}", "error")
        finally:
            if 'cur' in locals() and cur:
                cur.close()
            if conn:
                conn.close()
    
    global system_on
    
    return render_template(
        "home.html",
        table_rows=rows,
        system_on=system_on,
        username=session['username'],
        current_status=current_status,
        datetime=datetime
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah berhasil logout", "success")
    return redirect(url_for('index'))

@app.route("/system_status")
def get_system_status():
    global system_on
    return jsonify({"status": "ON" if system_on else "OFF"})

@app.route("/toggle_system", methods=["POST"])
@login_required
def toggle_system():
    global system_on
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Koneksi database gagal"}), 500
    try:
        payload = request.get_json()
        new_status_str = payload.get("status_system")

        if new_status_str not in ["ON", "OFF"]:
            return jsonify({"error": "Status tidak valid"}), 400
        
        system_on = (new_status_str == "ON")

        cur = conn.cursor()

        cur.execute("SELECT MAX(id) FROM jemuran_data")
        max_id_result = cur.fetchone()
        max_id = max_id_result[0] if max_id_result and max_id_result[0] else None

        if max_id is not None:
            sql = "UPDATE jemuran_data SET status_system = %s WHERE id = %s"
            cur.execute(sql, (new_status_str, max_id))
            conn.commit()
        
        cur.close()
        return jsonify({"message": f"Sistem diubah ke {new_status_str}", "new_system_status": new_status_str})
    except Error as e:
        return jsonify({"error": f"Kesalahan database saat mengubah status sistem: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Kesalahan server saat mengubah status sistem: {e}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/data")
@login_required
def get_data():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Koneksi database gagal"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 1")
        latest_data = cur.fetchone()

        cur.execute("SELECT id, waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 100")
        history_data = cur.fetchall()

        cur.close()
        conn.close()
        
        global system_on
        return jsonify({
            "latest": latest_data,
            "history": history_data,
            "flask_system_status": "ON" if system_on else "OFF"
        })
    except Error as e:
        return jsonify({"error": f"Kesalahan query database: {e}"}), 500

@app.route("/insert", methods=["POST"])
def insert_data():
    try:
        payload = request.get_json(force=True)
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")
        rain_value = payload.get("rain_value")
        ldr_value = payload.get("ldr_value")
        status_jemuran = payload.get("status_jemuran")
        system_status_from_arduino = payload.get("status_system")

        if any(v is None for v in [temperature, humidity, rain_value, ldr_value, status_jemuran, system_status_from_arduino]):
            return jsonify({"error": "Parameter tidak lengkap"}), 400
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Koneksi database gagal saat memasukkan data"}), 500
        
        cur = conn.cursor()
        sql = """
            INSERT INTO jemuran_data (waktu, temperature, humidity, rain_value, ldr_value, status_jemuran, status_system)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            float(temperature),
            float(humidity),
            int(rain_value),
            int(ldr_value),
            status_jemuran,
            system_status_from_arduino
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data berhasil dimasukkan"})
    except mysql.connector.Error as e:
        return jsonify({"error": f"Kesalahan MySQL: {e}"}), 500
    except Exception as ex:
        return jsonify({"error": f"Kesalahan server: {ex}"}), 500

@app.route("/rain_status", methods=["GET", "POST"])
def rain_status():
    global rain_status_from_hp
    if request.method == "POST":
        try:
            payload = request.get_json(force=True)
            status = payload.get("status")
            if status not in ["RAIN", "NO_RAIN"]:
                return jsonify({"error": "Status tidak valid"}), 400
            rain_status_from_hp = status
            return jsonify({"message": f"Status hujan diterima: {status}"})
        except Exception as e:
            return jsonify({"error": f"Kesalahan server: {e}"}), 500
    else:
        return jsonify({"status": rain_status_from_hp})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)