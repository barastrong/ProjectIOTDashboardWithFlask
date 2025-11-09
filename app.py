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
DB_NAME = os.getenv("DB_NAME", "percobaan")

app = Flask(__name__, template_folder="templates")
app.secret_key = 'ganti-dengan-kunci-rahasia-yang-unik'

system_on = True

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
            flash("Tidak dapat terhubung ke database. Silakan coba lagi nanti.")
            return redirect(url_for('index'))
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('home'))
            else:
                flash("Username atau password salah")
        except Error as e:
            flash(f"Terjadi kesalahan pada database: {e}")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/home')
@login_required
def home():
    rows = []
    conn = get_connection()
    if not conn:
        flash("Gagal terhubung ke database untuk memuat data.", "error")
    else:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, waktu, rain_value, ldr_value, status, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 100")
            rows = cur.fetchall()
        except Error as e:
            flash(f"Gagal memuat data: {e}", "error")
        finally:
            cur.close()
            conn.close()
    return render_template("home.html", table_rows=rows, system_on=system_on, username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah berhasil logout")
    return redirect(url_for('index'))

@app.route("/system_status")
@login_required
def get_system_status():
    global system_on
    return jsonify({"status": "ON" if system_on else "OFF"})

@app.route("/toggle_system", methods=["POST"])
@login_required
def toggle_system():
    global system_on
    try:
        payload = request.get_json(silent=True) or {}
        new_status = payload.get("status_system")
        if new_status not in ["ON", "OFF"]:
            return jsonify({"error": "Status tidak valid"}), 400
        system_on = (new_status == "ON")
        return jsonify({"message": f"Sistem diubah ke {new_status}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/data")
@login_required
def get_data():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Koneksi database gagal"}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, waktu, rain_value, ldr_value, status, status_system FROM jemuran_data ORDER BY waktu DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Error as e:
        return jsonify({"error": f"Kesalahan query database: {e}"}), 500

@app.route("/insert", methods=["POST"])
def insert_data():
    try:
        payload = request.get_json(force=True)
        rain_value = payload.get("rain_value")
        ldr_value = payload.get("ldr_value")
        status = payload.get("status")
        status_system_int = payload.get("status_system")

        if any(v is None for v in [rain_value, ldr_value, status, status_system_int]):
            return jsonify({"error": "Parameter tidak lengkap"}), 400
        
        status_system = "ON" if status_system_int == 1 else "OFF"
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Koneksi database gagal saat memasukkan data"}), 500
        
        cur = conn.cursor()
        sql = "INSERT INTO jemuran_data (waktu, rain_value, ldr_value, status, status_system) VALUES (%s, %s, %s, %s, %s)"
        cur.execute(sql, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(rain_value), int(ldr_value), status, status_system))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data berhasil dimasukkan"})
    except mysql.connector.Error as e:
        return jsonify({"error": f"Kesalahan MySQL: {e}"}), 500
    except Exception as ex:
        return jsonify({"error": f"Kesalahan server: {ex}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)