import socket
import time

# Konfiguracija Servera
SERVER_IP = '127.0.0.1'
SERVER_PORT = 7000

# Simuliramo da šaljemo sa Glavnog Ulaza
# (Mora se poklapati sa IP adresom iz baze/seed-a)
GATE_IP = "127.0.0.10" 

# Test Podaci: (Tip, Vrednost)
# Ovde unesi podatke koji postoje u tvojoj bazi za nekog test korisnika
TEST_SCANS = [
    ("RFID", "1234"),        # 1. Prislanja Karticu
    ("LPR",  "BG-101-DIR"),     # 2. Kamera vidi Tablicu
    ("QR",   "101")     # 3. Skenira QR kod
]

def send_scan(ctype, value):
    print(f"📡 [Slanje] {ctype}: {value} sa rampe {GATE_IP}...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # IP Spoofing: Vezujemo se za IP adresu rampe
        # (Ovo je ključno da bi Backend znao NA KOJOJ rampi se ovo dešava)
        try:
            s.bind((GATE_IP, 0))
        except OSError:
            print(f"⚠️  UPOZORENJE: Ne mogu da bindujem IP {GATE_IP}. Backend možda neće prepoznati Gejt.")
        
        s.connect((SERVER_IP, SERVER_PORT))
        
        # Format poruke koji naš Forwarder očekuje: "TIP:VREDNOST"
        payload = f"{ctype}:{value}"
        
        s.send(payload.encode('utf-8'))
        s.close()
        print("✅ Poslato.")
        
    except Exception as e:
        print(f"❌ Greška pri konekciji: {e}")

if __name__ == "__main__":
    print("--- 🧪 MULTIMODALNI TEST (RFID + LPR + QR) ---")
    print("Simuliramo jednog korisnika koji koristi različite metode ulaza.\n")

    for ctype, cval in TEST_SCANS:
        send_scan(ctype, cval)
        
        # Pravimo pauzu od 2 sekunde da lepo vidiš logove na ekranu
        # i da izbegnemo Debounce (20s) ako testiraš iste vrednosti
        time.sleep(2) 
        
    print("\n🏁 Test završen.")