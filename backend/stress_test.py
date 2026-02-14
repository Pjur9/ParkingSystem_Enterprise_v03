# backend/stress_test.py
import socket
import time
import random
import sys

# --- KONFIGURACIJA METE ---
SERVER_IP = '127.0.0.1'
SERVER_PORT = 7000

# --- IMENIK UREĐAJA (Mora se poklapati sa seed_heavy.py) ---
GATES = [
    {"ip": "127.0.0.10", "name": "Glavni Ulaz 1"},
    {"ip": "127.0.0.11", "name": "Glavni Izlaz 1"},
    {"ip": "127.0.0.12", "name": "Ulaz Garaža"},
    {"ip": "127.0.0.13", "name": "Izlaz Garaža"},
    {"ip": "127.0.0.14", "name": "Službeni Ulaz"},
    {"ip": "127.0.0.15", "name": "VIP Rampa"},
]

# --- BAZA KARTICA (Uzorkovano iz seed_heavy.py) ---
# Ovo su validne kartice koje smo kreirali
VALID_CREDS = []
VALID_CREDS += [f"DIR-{100+i}" for i in range(5)]         # Direktori
VALID_CREDS += [f"EMP-{500+i}" for i in range(20)]        # Zaposleni RFID
VALID_CREDS += [f"BG-{2000+i}-AS" for i in range(10)]     # Zaposleni LPR
VALID_CREDS += [f"TICKET-{9000+i}" for i in range(50)]    # Gosti
VALID_CREDS += [f"BANNED-{i}" for i in range(5)]          # Blokirani

# --- NEPOZNATE KARTICE (Hakeri) ---
INVALID_CREDS = ["HACKER-001", "UNKNOWN-999", "CLONED-CARD-X", "OLD-TICKET"]

def get_random_credential():
    # 80% šanse da je validna kartica, 20% da je nepoznata/neispravna
    if random.random() < 0.8:
        return random.choice(VALID_CREDS)
    return random.choice(INVALID_CREDS)

def send_scan():
    # 1. Izaberi nasumičnu rampu
    gate = random.choice(GATES)
    source_ip = gate['ip']
    
    # 2. Izaberi nasumičnu karticu
    card_code = get_random_credential()
    
    # 3. Odredi tip poruke na osnovu formata koda
    prefix = "RFID"
    if "BG-" in card_code: prefix = "LPR"
    elif "TICKET" in card_code: prefix = "QR"
    
    payload = f"{prefix}:{card_code}"
    
    print(f"🚀 [Slanje] {source_ip} ({gate['name']}) -> {payload}")

    try:
        # KREIRANJE SOCKET-a
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # --- KLJUČNI DEO: SPOOFING IP ADRESE ---
        # Bindujemo socket na specifičnu lokalnu adresu da bi Backend znao ko smo.
        # Ovo radi na Windowsu jer 127.0.0.X range pripada loopback-u.
        try:
            s.bind((source_ip, 0)) 
        except Exception as e:
            print(f"⚠️  Ne mogu da bindujem {source_ip}. Pokrećem bez toga (Možda treba Admin?). Greška: {e}")
            # Nastavljamo i bez bind-a, ali Backend možda neće prepoznati gejt ako gleda IP
        
        s.connect((SERVER_IP, SERVER_PORT))
        s.send(payload.encode('utf-8'))
        s.close()
        
    except Exception as e:
        print(f"❌ Greška pri konekciji: {e}")

if __name__ == "__main__":
    print("--- 🌪️ PARKING OS STRESS TEST V3.0 🌪️ ---")
    print(f"🎯 Target: {SERVER_IP}:{SERVER_PORT}")
    print(f"⏱️  Interval: 10-30 skenova po minuti (svakih 2-6 sekundi)")
    print("------------------------------------------------")

    try:
        while True:
            send_scan()
            
            # Pauza izmedju 2 i 6 sekundi (daje prosek oko 15-20 u minuti)
            sleep_time = random.uniform(2, 6)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n🛑 Test zaustavljen.")