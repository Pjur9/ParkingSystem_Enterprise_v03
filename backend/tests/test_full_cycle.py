# backend/tests/test_full_cycle.py
import time
import sys
import os
import random
from datetime import datetime

# Setup putanje
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Zone, Gate, Credential, Role, ParkingSession, ValidationRule, RuleType, RuleScope
from services.parking_service import ParkingLogicService

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def run_full_cycle_simulation():
    print(f"{Colors.HEADER}\n🔄 STARTING FULL CYCLE SIMULATION (Entry -> Exit -> Re-entry){Colors.ENDC}")
    
    app, _ = create_app()
    app.config['TESTING'] = True
    
    # Koristimo pravi servis (bez socketa da ne puca)
    service = ParkingLogicService(socketio=None)

    with app.app_context():
        # --- 1. SETUP OKRUŽENJA ---
        print(f"\n{Colors.OKBLUE}[1] SETUP ENVIRONMENT{Colors.ENDC}")
        
        # 1.1 Pravila (Get or Create)
        # Prvo brišemo stara pravila da ne smetaju
        db.session.query(ValidationRule).delete()
        
        # Dodajemo sveža pravila
        r1 = ValidationRule(rule_type=RuleType.CHECK_CAPACITY, scope=RuleScope.GLOBAL, is_enabled=True)
        r2 = ValidationRule(rule_type=RuleType.CHECK_ANTIPASSBACK, scope=RuleScope.GLOBAL, is_enabled=True)
        db.session.add_all([r1, r2])
        
        # 1.2 Rola (Get or Create)
        role = Role.query.filter_by(name="Guest").first()
        if not role:
            role = Role(name="Guest")
            db.session.add(role)
            db.session.commit() # Commit da dobijemo ID
        
        # 1.3 Random suffix da izbegnemo konflikte u bazi
        unique_id = random.randint(10000, 99999)

        # 1.4 User & Credential
        # Čistimo starog usera ako postoji (Clean slate)
        old_u = User.query.filter(User.last_name.like(f"Sofer_{unique_id}")).first()
        if old_u:
            db.session.delete(old_u)
            db.session.commit()

        user = User(first_name="Dragan", last_name=f"Sofer_{unique_id}", role_id=role.id, is_active=True)
        db.session.add(user)
        db.session.commit()
        
        cred_val = f"TAG_CYCLE_{unique_id}"
        cred = Credential(user_id=user.id, cred_type="RFID", cred_value=cred_val, is_active=True)
        db.session.add(cred)
        
        # 1.5 Zona (Kapacitet 10)
        zone_name = f"Cycle Zone {unique_id}"
        zone = Zone(name=zone_name, capacity=10, occupancy=0)
        db.session.add(zone)
        db.session.commit()

        # 1.6 Gejtovi
        gate_entry = Gate(name=f"Ulaz {unique_id}", zone_to_id=zone.id, zone_from_id=None)
        gate_exit = Gate(name=f"Izlaz {unique_id}", zone_to_id=None, zone_from_id=zone.id)
        
        db.session.add_all([gate_entry, gate_exit])
        db.session.commit()
        
        # Čuvamo ID-eve za kasnije
        entry_id = gate_entry.id
        exit_id = gate_exit.id
        zone_id = zone.id
        user_id = user.id

        print(f"   User: {user.first_name} {user.last_name}")
        print(f"   Credential: {cred_val}")
        print(f"   Zone: {zone.name} (0/10)")

        # --- 2. ULAZAK (ENTRY) ---
        print(f"\n{Colors.OKBLUE}[2] ATTEMPTING ENTRY...{Colors.ENDC}")
        # Reset cache-a
        import services.parking_service
        services.parking_service.SCAN_CACHE = {}

        result = service.handle_scan(entry_id, "RFID", cred_val)
        
        if result['allow']:
            print(f"{Colors.OKGREEN}   ✅ ENTRY APPROVED.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}   ❌ ENTRY FAILED: {result['reason']}{Colors.ENDC}")
            return

        # Provera stanja
        z = db.session.get(Zone, zone_id)
        # Refresh zone instance
        db.session.refresh(z)
        
        s = ParkingSession.query.filter_by(user_id=user_id, exit_time=None).first()
        print(f"   Zone Occupancy: {z.occupancy}/10 (Expected: 1)")
        print(f"   Active Session: {'YES' if s else 'NO'}")

        if z.occupancy != 1 or not s:
            print(f"{Colors.FAIL}   ❌ STATE ERROR: Occupancy or Session missing.{Colors.ENDC}")
            return

        # --- 3. POKUŠAJ PREVARE (PASSBACK) ---
        print(f"\n{Colors.OKBLUE}[3] ATTEMPTING PASSBACK (Scanning Entry again)...{Colors.ENDC}")
        # Moramo očistiti keš da ne bi dobili DEBOUNCE
        services.parking_service.SCAN_CACHE = {} 

        result = service.handle_scan(entry_id, "RFID", cred_val)
        
        if not result['allow'] and result['reason'] == "ALREADY_INSIDE":
            print(f"{Colors.OKGREEN}   ✅ PASSBACK BLOCKED Correctly ({result['reason']}).{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}   ❌ SECURITY HOLE! User entered twice! Result: {result}{Colors.ENDC}")
            return

        # --- 4. SIMULACIJA VREMENA ---
        print(f"\n{Colors.OKBLUE}[4] PARKING TIME (Sleeping 2s)...{Colors.ENDC}")
        time.sleep(2)

        # --- 5. IZLAZAK (EXIT) ---
        print(f"\n{Colors.OKBLUE}[5] ATTEMPTING EXIT...{Colors.ENDC}")
        services.parking_service.SCAN_CACHE = {} 
        
        result = service.handle_scan(exit_id, "RFID", cred_val)
        
        if result['allow']:
             print(f"{Colors.OKGREEN}   ✅ EXIT APPROVED.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}   ❌ EXIT FAILED: {result['reason']}{Colors.ENDC}")
            return

        # Provera stanja nakon izlaza
        z = db.session.get(Zone, zone_id)
        db.session.refresh(z)
        
        s = ParkingSession.query.filter_by(user_id=user_id).order_by(ParkingSession.id.desc()).first()
        
        print(f"   Zone Occupancy: {z.occupancy}/10 (Expected: 0)")
        print(f"   Session Closed: {'YES' if s.exit_time else 'NO'}")
        
        duration = (s.exit_time - s.entry_time).total_seconds()
        print(f"   Duration: {duration:.2f} seconds")

        if z.occupancy != 0 or not s.exit_time:
             print(f"{Colors.FAIL}   ❌ STATE ERROR: Zone not empty or session active.{Colors.ENDC}")
             return

        # --- 6. POVRATAK (RE-ENTRY) ---
        print(f"\n{Colors.OKBLUE}[6] ATTEMPTING RE-ENTRY (Next Day)...{Colors.ENDC}")
        services.parking_service.SCAN_CACHE = {} 

        result = service.handle_scan(entry_id, "RFID", cred_val)
        
        if result['allow']:
             print(f"{Colors.OKGREEN}   ✅ RE-ENTRY APPROVED (Cycle Complete).{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}   ❌ RE-ENTRY FAILED: {result['reason']}{Colors.ENDC}")
            return
        
        # --- CLEANUP ---
        print(f"\n{Colors.OKBLUE}[7] CLEANUP...{Colors.ENDC}")
        # Delete Session
        ParkingSession.query.filter_by(user_id=user_id).delete()
        # Delete Gates
        db.session.delete(db.session.get(Gate, entry_id))
        db.session.delete(db.session.get(Gate, exit_id))
        # Delete Zone
        db.session.delete(db.session.get(Zone, zone_id))
        # Delete Cred & User
        db.session.delete(db.session.get(Credential, cred.id))
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()

        print(f"\n{Colors.HEADER}🏆 SIMULATION SUCCESSFUL! System Logic is Perfect.{Colors.ENDC}")

if __name__ == "__main__":
    run_full_cycle_simulation()