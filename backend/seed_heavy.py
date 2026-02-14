# backend/seed_heavy.py
from app import app
from models import (
    db, User, Role, Tenant, Zone, Gate, Device, 
    ValidationRule, Credential, RuleScope, RuleType, CredentialType
)
import random

def seed_heavy():
    with app.app_context():
        print("💣 BRISANJE CELOKUPNE BAZE...")
        db.drop_all()
        print("🏗️  KREIRANJE NOVE STRUKTURE...")
        db.create_all()

        # --- 1. ROLES ---
        roles = {
            "admin": Role(name="Admin", description="System God", can_ignore_capacity=True, can_ignore_antipassback=True),
            "vip": Role(name="VIP", description="Diplomats & Directors", can_ignore_capacity=True, can_ignore_antipassback=False),
            "staff": Role(name="Staff", description="Airport Employees", can_ignore_capacity=False, can_ignore_antipassback=False),
            "guest": Role(name="Guest", description="Hourly Parking", is_billable=True),
            "banned": Role(name="Blacklisted", description="Banned Users")
        }
        db.session.add_all(roles.values())
        db.session.commit()

        # --- 2. TENANTS ---
        tenants = [
            Tenant(name="AirSerbia HQ", quota_limit=50),
            Tenant(name="WizzAir Ops", quota_limit=20),
            Tenant(name="Hertz Rent-a-Car", quota_limit=100)
        ]
        db.session.add_all(tenants)
        db.session.commit()

        # --- 3. ZONES (HIERARCHY) ---
        # Root
        z_airport = Zone(name="Aerodrom Kompleks", capacity=2000, occupancy=0)
        db.session.add(z_airport)
        db.session.commit()

        # Level 1 (Public)
        z_public = Zone(name="Javna Garaža", capacity=500, parent_zone_id=z_airport.id)
        db.session.add(z_public)
        
        # Level 1 (Staff Only)
        z_staff = Zone(name="Službeni Parking", capacity=200, parent_zone_id=z_airport.id)
        db.session.add(z_staff)
        db.session.commit()

        # Level 2 (Inside Staff)
        z_vip = Zone(name="VIP & Directors", capacity=20, parent_zone_id=z_staff.id)
        db.session.add(z_vip)
        db.session.commit()

        # --- 4. GATES & DEVICES (IP MAPPING) ---
        # Za simulaciju cemo koristiti 127.0.0.X adrese
        gates_config = [
            # Ime, From, To, IP
            ("Glavni Ulaz 1", None, z_airport.id, "127.0.0.10"),
            ("Glavni Izlaz 1", z_airport.id, None, "127.0.0.11"),
            ("Ulaz Garaža", z_airport.id, z_public.id, "127.0.0.12"),
            ("Izlaz Garaža", z_public.id, z_airport.id, "127.0.0.13"),
            ("Službeni Ulaz", z_airport.id, z_staff.id, "127.0.0.14"),
            ("VIP Rampa", z_staff.id, z_vip.id, "127.0.0.15")
        ]

        for g_name, z_from, z_to, ip in gates_config:
            gate = Gate(name=g_name, zone_from_id=z_from, zone_to_id=z_to)
            db.session.add(gate)
            db.session.commit()
            
            # Device vezan za ovaj gate
            dev = Device(name=f"Reader-{g_name}", ip_address=ip, gate_id=gate.id, device_type="controller")
            db.session.add(dev)
        
        db.session.commit()

        # --- 5. USERS GENERATOR (150+) ---
        print("👥 GENERISANJE 150+ KORISNIKA...")
        
        generated_creds = []

        # A. Kreiraj 5 Direktora (VIP)
        for i in range(5):
            u = User(first_name="Direktor", last_name=f"Broj {i+1}", role_id=roles['vip'].id)
            db.session.add(u)
            db.session.commit()
            c = Credential(user_id=u.id, cred_type=CredentialType.RFID, cred_value=f"DIR-{100+i}")
            db.session.add(c)
            generated_creds.append(c.cred_value)

        # B. Kreiraj 50 Zaposlenih (AirSerbia)
        for i in range(50):
            u = User(first_name="Pilot", last_name=f"Jovan {i+1}", role_id=roles['staff'].id, tenant_id=tenants[0].id)
            db.session.add(u)
            db.session.commit()
            # Svaki 3. ima Tablicu (LPR), ostali RFID
            ctype = CredentialType.LPR if i % 3 == 0 else CredentialType.RFID
            cval = f"BG-{2000+i}-AS" if ctype == CredentialType.LPR else f"EMP-{500+i}"
            c = Credential(user_id=u.id, cred_type=ctype, cred_value=cval)
            db.session.add(c)
            generated_creds.append(cval)

        # C. Kreiraj 100 Gostiju (QR Kodovi)
        for i in range(100):
            u = User(first_name="Gost", last_name=f"Petar {i+1}", role_id=roles['guest'].id)
            db.session.add(u)
            db.session.commit()
            c = Credential(user_id=u.id, cred_type=CredentialType.QR, cred_value=f"TICKET-{9000+i}")
            db.session.add(c)
            generated_creds.append(c.cred_value)
            
        # D. Kreiraj 5 Blokiranih (Lopovi)
        for i in range(5):
             u = User(first_name="LOPOV", last_name=f"Banned {i+1}", role_id=roles['banned'].id)
             db.session.add(u)
             db.session.commit()
             c = Credential(user_id=u.id, cred_type=CredentialType.RFID, cred_value=f"BANNED-{i}")
             db.session.add(c)
             generated_creds.append(c.cred_value)

        db.session.commit()
        
        # --- 6. PRAVILA ---
        print("🧠 POSTAVLJANJE PRAVILA...")
        # Blacklist check (Global)
        r1 = ValidationRule(scope=RuleScope.GLOBAL, rule_type=RuleType.CHECK_BLACKLIST, is_enabled=True)
        # Antipassback (Staff Zone)
        r2 = ValidationRule(scope=RuleScope.ZONE, target_zone_id=z_staff.id, rule_type=RuleType.CHECK_ANTIPASSBACK, is_enabled=True)
        # Capacity (Public Garage)
        r3 = ValidationRule(scope=RuleScope.ZONE, target_zone_id=z_public.id, rule_type=RuleType.CHECK_CAPACITY, is_enabled=True)
        
        db.session.add_all([r1, r2, r3])
        db.session.commit()

        print("✅ SEED ZAVRŠEN!")
        print(f"   - Ukupno korisnika: {5+50+100+5}")
        print(f"   - Gates IP Range: 127.0.0.10 - 127.0.0.15")

if __name__ == "__main__":
    seed_heavy()