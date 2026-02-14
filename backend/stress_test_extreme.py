# backend/stress_test_extreme.py
import socket
import time
import random
import threading

SERVER_IP = '127.0.0.1'
SERVER_PORT = 7000

# Iste rampe kao u seed-u
GATES = [
    {"ip": "127.0.0.10", "name": "Glavni Ulaz 1"},
    {"ip": "127.0.0.11", "name": "Glavni Izlaz 1"},
    {"ip": "127.0.0.12", "name": "Ulaz Garaža"},
    {"ip": "127.0.0.13", "name": "Izlaz Garaža"},
    {"ip": "127.0.0.14", "name": "Službeni Ulaz"},
    {"ip": "127.0.0.15", "name": "VIP Rampa"},
]

# Koristimo samo RFID kartice za brzinu
USERS = [f"EMP-{500+i}" for i in range(50)] # 50 Zaposlenih

def send_packet(gate, card_code):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Pokušaj IP spoofing-a
        try: s.bind((gate['ip'], 0))
        except: pass
        
        s.connect((SERVER_IP, SERVER_PORT))
        msg = f"RFID:{card_code}"
        s.send(msg.encode('utf-8'))
        s.close()
        print(f"⚡ [EXTREME] {gate['name']} -> {card_code}")
    except Exception as e:
        print(f"❌ Greška: {e}")

def attack_mode():
    """Simulira gužvu u špicu (8:00 ujutru)"""
    while True:
        # Nasumičan korisnik i nasumična rampa
        user = random.choice(USERS)
        gate = random.choice(GATES)
        
        send_packet(gate, user)
        
        # Veoma kratka pauza (0.1 do 0.5 sekundi)
        time.sleep(random.uniform(0.1, 0.5))

def race_condition_attack():
    """Pokušava da uđe sa istom karticom na dve rampe ISTOVREMENO"""
    while True:
        user = random.choice(USERS)
        g1 = GATES[0] # Glavni ulaz
        g2 = GATES[4] # Službeni ulaz
        
        print(f"⚔️ RACE ATTACK: {user} pokušava ulaz na 2 mesta odjednom!")
        
        # Dve niti šalju zahtev u istom trenutku
        t1 = threading.Thread(target=send_packet, args=(g1, user))
        t2 = threading.Thread(target=send_packet, args=(g2, user))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        time.sleep(5) # Odmori malo posle napada

if __name__ == "__main__":
    print("💀 POKREĆEM EXTREME STRESS TEST...")
    print("1. Standardni brzi saobraćaj")
    print("2. Race Condition napad (Isti user, 2 rampe)")
    
    # Pokrećemo oba moda paralelno u threadovima
    t_traffic = threading.Thread(target=attack_mode)
    t_race = threading.Thread(target=race_condition_attack)
    
    t_traffic.start()
    t_race.start()