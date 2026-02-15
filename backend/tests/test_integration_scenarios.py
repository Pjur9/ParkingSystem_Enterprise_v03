# backend/tests/test_advanced_scenarios.py
import socket
import time
import sys
import os

# Dodajemo parent folder u path da mozemo importovati app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Device, Zone, Tenant, Credential
from services.forwarder_tcp import ForwarderIngressServer

# KONFIGURACIJA
FORWARDER_IP = "127.0.0.1"
FORWARDER_PORT = 7000
MOCK_CONTROLLER_PORT = 5005

class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def send_scan_signal(payload):
    """Šalje TCP poruku Forwarderu"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((FORWARDER_IP, FORWARDER_PORT))
            s.sendall(payload.encode())
        print(f"   📡 Sent scan: {payload}")
        time.sleep(0.5) # Wait for processing
    except Exception as e:
        print(f"{Colors.FAIL}Connection failed: {e}{Colors.ENDC}")

def get_last_log_status(app):
    """Vraća status zadnjeg loga iz baze"""
    from models import ScanLog
    with app.app_context():
        log = ScanLog.query.order_by(ScanLog.timestamp.desc()).first()
        if log:
            return log.is_access_granted, log.denial_reason
        return None, None

def run_advanced_tests():
    app, _ = create_app()
    
    print(f"{Colors.HEADER}🚀 STARTING ADVANCED EDGE-CASE TESTS{Colors.ENDC}")
    
    with app.app_context():
        # --- SETUP: OSIGURAJ DA IMAMO TEST PODATKE ---
        # 1. Device na localhost
        device = Device.query.first()
        if device.ip_address != "127.0.0.1":
            print(f"{Colors.WARNING}⚠️  Setting Device {device.name} IP to 127.0.0.1 for testing...{Colors.ENDC}")
            device.ip_address = "127.0.0.1"
            device.port = 5005
            db.session.commit()

        # 2. Korisnici
        staff_user = User.query.filter(User.role.has(name="Staff")).first()
        vip_user = User.query.filter(User.role.has(name="VIP")).first()
        
        if not staff_user or not vip_user:
            print(f"{Colors.FAIL}❌ Missing STAFF or VIP users in DB. Run seed_heavy.py first.{Colors.ENDC}")
            return

        staff_card = staff_user.credentials[0].cred_value
        vip_card = vip_user.credentials[0].cred_value
        
        # 3. Zona
        main_zone = device.gate.zone_to # Zona u koju ulazimo
        if not main_zone:
            print(f"{Colors.FAIL}❌ Device is not an Entry Gate (No zone_to).{Colors.ENDC}")
            return

        print(f"🧪 Testing Zone: {main_zone.name} (Capacity: {main_zone.capacity})")
        print(f"👤 Staff Card: {staff_card}")
        print(f"🌟 VIP Card:   {vip_card}")

        # ---------------------------------------------------------
        # TEST 1: KAPACITET ZONE (ZONE FULL)
        # ---------------------------------------------------------
        print(f"\n{Colors.HEADER}--- TEST 1: ZONE FULL (Capacity Limit) ---{Colors.ENDC}")
        
        # Postavljamo zonu da bude puna
        original_occupancy = main_zone.occupancy
        main_zone.occupancy = main_zone.capacity 
        db.session.commit()
        print(f"   🔧 Setup: Manually filled zone ({main_zone.occupancy}/{main_zone.capacity})")

        send_scan_signal(staff_card)
        
        allowed, reason = get_last_log_status(app)
        if not allowed and reason == "ZONE_FULL":
            print(f"{Colors.OKGREEN}✅ PASS: Regular user denied because zone is full.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL: User was {allowed} (Reason: {reason}). Expected: DENIED/ZONE_FULL{Colors.ENDC}")

        # ---------------------------------------------------------
        # TEST 2: VIP OVERRIDE (VIP ulazi i kad je puno)
        # ---------------------------------------------------------
        print(f"\n{Colors.HEADER}--- TEST 2: VIP OVERRIDE ---{Colors.ENDC}")
        
        # Zona je i dalje puna iz prethodnog testa
        send_scan_signal(vip_card)
        
        allowed, reason = get_last_log_status(app)
        if allowed:
            print(f"{Colors.OKGREEN}✅ PASS: VIP User allowed despite full zone.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL: VIP User was DENIED (Reason: {reason}).{Colors.ENDC}")

        # Vraćamo occupancy na staro
        main_zone.occupancy = 0
        db.session.commit()

        # ---------------------------------------------------------
        # TEST 3: INACTIVE USER (Otpušteni radnik)
        # ---------------------------------------------------------
        print(f"\n{Colors.HEADER}--- TEST 3: INACTIVE USER ---{Colors.ENDC}")
        
        # Deaktiviramo staff korisnika
        staff_user.is_active = False
        db.session.commit()
        print(f"   🔧 Setup: Deactivated user {staff_user.first_name}")

        send_scan_signal(staff_card)
        
        allowed, reason = get_last_log_status(app)
        if not allowed and reason == "USER_INACTIVE":
            print(f"{Colors.OKGREEN}✅ PASS: Inactive user denied.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL: User was {allowed} (Reason: {reason}). Expected: DENIED/USER_INACTIVE{Colors.ENDC}")

        # Vraćamo usera na active
        staff_user.is_active = True
        db.session.commit()

        # ---------------------------------------------------------
        # TEST 4: TENANT QUOTA (Firma popunila kvotu)
        # ---------------------------------------------------------
        print(f"\n{Colors.HEADER}--- TEST 4: TENANT QUOTA EXCEEDED ---{Colors.ENDC}")
        
        if staff_user.tenant:
            tenant = staff_user.tenant
            # Setujemo limit
            original_limit = tenant.quota_limit
            original_usage = tenant.current_usage
            
            tenant.quota_limit = 5
            tenant.current_usage = 5
            db.session.commit()
            print(f"   🔧 Setup: Tenant '{tenant.name}' full ({tenant.current_usage}/{tenant.quota_limit})")

            send_scan_signal(staff_card)
            
            allowed, reason = get_last_log_status(app)
            if not allowed and reason == "TENANT_QUOTA_EXCEEDED":
                print(f"{Colors.OKGREEN}✅ PASS: Tenant quota enforced.{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ FAIL: Result: {allowed}/{reason}. Expected: DENIED/TENANT_QUOTA_EXCEEDED{Colors.ENDC}")

            # Reset
            tenant.quota_limit = original_limit
            tenant.current_usage = original_usage
            db.session.commit()
        else:
            print(f"{Colors.WARNING}⚠️ SKIPPING: Staff user has no tenant assigned.{Colors.ENDC}")

    print(f"\n{Colors.HEADER}🏁 TESTS COMPLETED{Colors.ENDC}")

if __name__ == "__main__":
    run_advanced_tests()