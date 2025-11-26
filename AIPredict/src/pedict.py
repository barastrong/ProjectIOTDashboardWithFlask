import joblib
import pandas as pd
import os

# Dynamically resolve the MODEL_DIR relative to this file location
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Model'))

MODEL_PATH = os.path.join(MODEL_DIR, 'jemuran_ai_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'jemuran_ai_scaler.pkl')
ENCODER_PATH = os.path.join(MODEL_DIR, 'jemuran_ai_encoder.pkl')

# Inisialisasi variabel global untuk model, scaler, dan encoder
model = None
scaler = None
encoder = None
features = ['temperature', 'humidity', 'rain_value', 'ldr_value'] 

def load_model_artifacts():
    """Memuat model, scaler, dan encoder dari file .pkl."""
    global model, scaler, encoder
    try:
        # Pengecekan eksplisit apakah file-file ada
        if not os.path.exists(MODEL_PATH):
            print(f"ERROR: File model '{MODEL_PATH}' tidak ditemukan.")
            print("Pastikan Anda sudah menjalankan AIPredict.ipynb dan menyimpan model ke folder 'Model'.")
            model, scaler, encoder = None, None, None
            return

        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        encoder = joblib.load(ENCODER_PATH)
        print("Model, Scaler, dan Encoder berhasil dimuat!")
    except FileNotFoundError:
        # Ini sebenarnya sudah ditangani oleh os.path.exists, tapi jaga-jaga
        print(f"ERROR: File model tidak ditemukan di '{MODEL_DIR}'.")
        print("Pastikan Anda sudah menjalankan AIPredict.ipynb.")
        model, scaler, encoder = None, None, None
    except Exception as e:
        print(f"ERROR: Gagal memuat model: {e}")
        model, scaler, encoder = None, None, None

def get_prediction(temperature, humidity, rain_value, ldr_value):
    """
    Melakukan prediksi status jemuran berdasarkan input sensor.
    Mengembalikan status_jemuran (string) dan dictionary probabilitas.
    """
    # Jika model belum dimuat atau ada error, coba muat ulang
    if model is None or scaler is None or encoder is None:
        print("Model belum dimuat atau ada kesalahan. Mencoba memuat ulang...")
        load_model_artifacts() 
        if model is None: # Jika masih gagal setelah coba muat ulang
            return "Model tidak siap", {"Terjemur": 0.5, "Tertutup": 0.5} # Fallback

    # Buat DataFrame dari input sensor baru (pastikan urutan kolom sesuai 'features')
    new_data = pd.DataFrame([[temperature, humidity, rain_value, ldr_value]],
                            columns=features)
    
    # Scaling data baru menggunakan scaler yang sudah dilatih
    new_data_scaled = scaler.transform(new_data)
    
    # Lakukan prediksi
    prediction_encoded = model.predict(new_data_scaled)[0]
    prediction_proba = model.predict_proba(new_data_scaled)[0] # Array probabilitas

    # Dekode hasil prediksi kembali ke string asli
    predicted_status = encoder.inverse_transform([prediction_encoded])[0]

    # Buat dictionary probabilitas (misal: {'Terjemur': 0.7, 'Tertutup': 0.3})
    proba_dict = {encoder.classes_[i]: proba for i, proba in enumerate(prediction_proba)}
    
    return predicted_status, proba_dict

# Muat model saat script ini pertama kali diimpor atau dijalankan
load_model_artifacts()

if __name__ == '__main__':
    # Contoh penggunaan langsung (hanya untuk testing pedict.py)
    print("\n--- Testing pedict.py secara mandiri ---")
    
    # Contoh data sensor 1 (cenderung 'Tertutup' karena hujan dan gelap)
    # Sesuaikan nilai-nilai ini agar sesuai dengan rentang sensor Anda!
    status1, proba1 = get_prediction(temperature=25.0, humidity=90.0, rain_value=600, ldr_value=100)
    print(f"Prediksi 1: {status1}, Probabilitas: {proba1}")

    # Contoh data sensor 2 (cenderung 'Terjemur' karena cerah dan tidak hujan)
    status2, proba2 = get_prediction(temperature=30.0, humidity=70.0, rain_value=0, ldr_value=800)
    print(f"Prediksi 2: {status2}, Probabilitas: {proba2}")
