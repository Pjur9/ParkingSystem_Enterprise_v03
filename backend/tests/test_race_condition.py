# backend/tests/test_race_condition.py
import threading
import time
import pytest
import sys
import os
import random
from datetime import datetime

# Dodaj putanju do aplikacije
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Zone, Gate, Credential, Role, ParkingSession, ValidationRule, RuleType, RuleScope
from services.parking_service import ParkingLogicService

success_count = 0
capacity = 2 
denied_count = 0
errors = []
lock = threading.Lock()

def attempt_entry(app, gate_id, cred_value):
    global success_count, denied_count, errors
    with app.app_context():
        try:
            # Koristimo servis bez SocketIO (da ne puca na emit)
            service = ParkingLogicService(socketio=None) 
            result = service.handle_scan(gate_id, "RFID", cred_value)
            
            with lock:
                if result['allow']:
                    success_count += 1
                    print(f"✅ {threading.current_thread().name} -> ALLOWED")
                else:
                    denied_count += 1
                    print(f"❌ {threading.current_thread().name} -> DENIED ({result['reason']})")     
        except Exception as e:
            with lock:
                errors.append(str(e))
                print(f"🔥 CRASH {threading.current_thread().name}: {e}")

def run_race_condition_test():
    print("\n🏎️  STARTING RACE CONDITION TEST (5 Cars vs 1 Spot)...")
    app, _ = create_app()
    
    # ID-evi za cleanup
    target_zone_id = None
    target_gate_id = None
    target_user_id = None
    rule_ids = []

    with app.app_context():
        # --- 1. SETUP ---
        
        # A) Rola
        role = Role.query.filter_by(name="Guest").first()
        if not role:
            role = Role(name="Guest")
            db.session.add(role)
            db.session.commit()

        # B) Unique IDs
        unique_id = random.randint(1000, 9999)
        
        # C) Zona i Gate
        zone = Zone(name=f"Race Zone {unique_id}", capacity=capacity, occupancy=0)
        db.session.add(zone)
        db.session.commit()
        target_zone_id = zone.id

        gate = Gate(name=f"Race Gate {unique_id}", zone_to_id=zone.id)
        db.session.add(gate)
        db.session.commit()
        target_gate_id = gate.id
        
        # D) User i Kartice
        user = User(first_name="Racer", last_name=str(unique_id), role_id=role.id, is_active=True)
        db.session.add(user)
        db.session.commit()
        target_user_id = user.id

        creds = []
        for i in range(5):
            c_val = f"TAG_RACE_{unique_id}_{i}"
            cred = Credential(user_id=user.id, cred_type="RFID", cred_value=c_val, is_active=True)
            db.session.add(cred)
            creds.append(c_val)
        
        # E) PRAVILA (OVO JE FALILO!) 🚨
        # Bez ovoga sistem ne proverava kapacitet!
        rule = ValidationRule(rule_type=RuleType.CHECK_CAPACITY, scope=RuleScope.GLOBAL, is_enabled=True)
        db.session.add(rule)
        db.session.commit()
        rule_ids.append(rule.id)
        
        db.session.commit()

    # --- 2. NAPAD ---
    threads = []
    for i in range(5):
        t = threading.Thread(target=attempt_entry, args=(app, target_gate_id, creds[i]), name=f"Car-{i+1}")
        threads.append(t)
    
    start_time = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    end_time = time.time()
    
    # --- 3. ANALIZA I CLEANUP ---
    print("\n📊 RESULTS:")
    print(f"   Time taken: {end_time - start_time:.4f}s")
    print(f"   Success (Entered): {success_count}")
    print(f"   Denied: {denied_count}")
    
    with app.app_context():
        final_zone = db.session.get(Zone, target_zone_id)
        print(f"   Final DB Occupancy: {final_zone.occupancy}/{final_zone.capacity}")
        
        print("🧹 Cleaning up...")
        
        # 1. Prvo brišemo Sesije (Decu)
        db.session.query(ParkingSession).filter(ParkingSession.entry_gate_id == target_gate_id).delete()
        
        # 2. Brišemo Usera i Kartice
        if target_user_id:
            u = db.session.get(User, target_user_id)
            if u: db.session.delete(u)
        
        # 3. Brišemo Gate
        if target_gate_id:
            g = db.session.get(Gate, target_gate_id)
            if g: db.session.delete(g)
            
        # 4. Brišemo Zonu
        if final_zone:
            db.session.delete(final_zone)

        # 5. Brišemo Pravila
        for rid in rule_ids:
            r = db.session.get(ValidationRule, rid)
            if r: db.session.delete(r)
            
        db.session.commit()
        print("✅ Cleanup complete.")

        if success_count == capacity:
            print("\n🏆 TEST PASSED! System is Race-Condition safe.")
            return True
        else:
            print(f"\n❌ TEST FAILED! Race Condition detected! {success_count} cars entered.")
            return False

if __name__ == "__main__":
    run_race_condition_test()