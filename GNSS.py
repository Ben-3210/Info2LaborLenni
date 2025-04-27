import os
import time
import serial
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import psycopg2  # psycopg2

# -------------------------
# .env Datei laden
# -------------------------
load_dotenv(dotenv_path=Path.cwd() / ".env")

# -------------------------
# Konfiguration
# -------------------------
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/serial0")
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# -------------------------
# Funktionen
# -------------------------
def parse_gpgga(line):
    try:
        parts = line.split(',')
        if len(parts) < 10:
            return None

        lat_raw = parts[2]
        lat_dir = parts[3]
        lon_raw = parts[4]
        lon_dir = parts[5]
        alt = float(parts[9])

        lat = convert_to_decimal(lat_raw, lat_dir)
        lon = convert_to_decimal(lon_raw, lon_dir)

        return (lat, lon, alt)
    except:
        return None

def convert_to_decimal(raw, direction):
    if raw == '' or direction == '':
        return None
    deg = int(float(raw) / 100)
    min = float(raw) - deg * 100
    decimal = deg + min / 60
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

# -------------------------
# Hauptprogramm
# -------------------------
try:
    # GNSS-Verbindung öffnen
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("✅ GNSS-Sensor verbunden!")

    # Datenbank-Verbindung aufbauen
    db = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode="require"  # SSL erzwingen
    )
    cursor = db.cursor()
    print("✅ Mit Datenbank verbunden!")

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"Empfangen: {line}")  # Debug-Ausgabe hinzugefügt
            if '$GGA' in line:
                data = parse_gpgga(line)
                if data:
                    lat, lon, alt = data
                    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO gnss_data (timestamp, latitude, longitude, altitude)
                        VALUES (%s, %s, %s, %s)
                    """, (timestamp, lat, lon, alt))
                    db.commit()
                    print(f"🌍 Gespeichert: {timestamp} → {lat}, {lon}, {alt} m")
                else:
                    print("🕓 Noch kein GPS-Fix erhalten...")
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 GNSS-Logger beendet durch Tastatur")
            break

        except Exception as e:
            print(f"⚠️ Fehler während Datenbank-Update: {e}")
            time.sleep(2)

finally:
    print("\n📦 Aufräumen...")
    try:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
        if 'ser' in locals():
            ser.close()
    except Exception as e:
        print(f"⚠️ Fehler beim Aufräumen: {e}")