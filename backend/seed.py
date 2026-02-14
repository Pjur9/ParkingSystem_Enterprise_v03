from app import app
from models import (
    db, User, Role, Tenant, Zone, Gate, Device, 
    ValidationRule, Credential, ParkingSession,
    RuleScope, RuleType, CredentialType
)
from datetime import datetime

def seed_database():
    with app.app_context():
        print("🗑️  Brisanje stare baze...")
        db.drop_all()
        print("🏗️  Kreiranje nove V3.0 šeme...")
        db.create_all()

        # --- 1. KREIRANJE ROLA (RBAC) ---
        print("👤 Kreiranje Rola...")
        
        # Direktor: Bog otac (Ignoriše sve limite)
        r_director = Role(
            name="Direktor", 
            description="Uprava aerodroma",
            can_ignore_capacity=True,
            can_ignore_antipassback=True,
            can_ignore_schedule=True,
            is_billable=False
        )

        # Zaposleni: Standardna pravila, ali besplatno
        r_employee = Role(
            name="Zaposleni", 
            description="Osoblje i posada",
            can_ignore_capacity=False, # Mora da poštuje kvote
            can_ignore_antipassback=False,
            is_billable=False
        )

        # Gost: Najstroža pravila, plaća se
        r_guest = Role(
            name="Gost", 
            description="Putnici i posetioci",
            can_ignore_capacity=False,
            can_ignore_antipassback=False,
            is_billable=True
        )

        db.session.add_all([r_director, r_employee, r_guest])
        db.session.commit()

        # --- 2. KREIRANJE TENANTA (B2B) ---
        print("🏢 Kreiranje Tenanta...")
        
        t_airserbia = Tenant(name="AirSerbia", quota_limit=50, current_usage=0)
        t_wizzair = Tenant(name="WizzAir", quota_limit=20, current_usage=0)
        
        db.session.add_all([t_airserbia, t_wizzair])
        db.session.commit()

        # --- 3. KREIRANJE ZONA (HIJERARHIJA) ---
        print("lu  Kreiranje Zonske Hijerarhije...")

        # Root Zona
        # ISPRAVLJENO: 'current_usage' -> 'occupancy'
        z_airport = Zone(name="Aerodrom Kompleks", capacity=1000, occupancy=0)
        db.session.add(z_airport)
        db.session.commit() # Commit da dobijemo ID

        # Child Zona (Ugnježdena u Aerodrom)
        # ISPRAVLJENO: 'current_usage' -> 'occupancy'
        z_vip_garage = Zone(
            name="VIP Garaža", 
            capacity=10, 
            occupancy=0, 
            parent_zone_id=z_airport.id
        )
        db.session.add(z_vip_garage)
        db.session.commit()

        # --- 4. KREIRANJE GEJTOVA (FIZIKA KRETANJA) ---
        print("🚧 Kreiranje Gejtova...")

        # Glavni Ulaz (Iz Sveta -> Aerodrom)
        g_main_entry = Gate(
            name="Glavni Ulaz 1",
            zone_from_id=None,      # Dolazi spolja
            zone_to_id=z_airport.id # Ulazi u kompleks
        )

        # Glavni Izlaz (Iz Aerodroma -> Svet)
        g_main_exit = Gate(
            name="Glavni Izlaz 1",
            zone_from_id=z_airport.id,
            zone_to_id=None
        )

        # Interni VIP Ulaz (Iz Aerodroma -> VIP Garaža)
        g_vip_entry = Gate(
            name="VIP Rampa Ulaz",
            zone_from_id=z_airport.id, # Moraš biti u kompleksu da bi ušao ovde
            zone_to_id=z_vip_garage.id
        )

        db.session.add_all([g_main_entry, g_main_exit, g_vip_entry])
        db.session.commit()
        
        # --- 4.1 KREIRANJE UREĐAJA (Bitno za simulaciju) ---
        print("🔌 Kreiranje Uređaja...")
        
        # Simuliramo da je tvoj lokalni PC (127.0.0.1) zapravo kontroler za VIP rampu
        d_vip_controller = Device(
            name="VIP Controller",
            ip_address="127.0.0.1",
            port=5000,
            device_type="controller",
            gate_id=g_vip_entry.id
        )
        db.session.add(d_vip_controller)
        db.session.commit()


        # --- 5. KREIRANJE PRAVILA (LOGIC ENGINE) ---
        print("🧠 Konfigurisanje Logic Engine-a...")

        # A. GLOBALNO PRAVILO: "Demo Dan" - Isključi plaćanje svuda
        rule_demo = ValidationRule(
            scope=RuleScope.GLOBAL,
            rule_type=RuleType.CHECK_PAYMENT,
            is_enabled=False, # <-- DEMO MODE: ON
            custom_params='{"reason": "Open Day 2024"}'
        )

        # B. ZONSKO PRAVILO: VIP Garaža strogo gleda kapacitet
        rule_vip_cap = ValidationRule(
            scope=RuleScope.ZONE,
            target_zone_id=z_vip_garage.id,
            rule_type=RuleType.CHECK_CAPACITY,
            is_enabled=True
        )

        # C. ROLA PRAVILO: Gosti moraju poštovati Anti-Passback
        rule_guest_apb = ValidationRule(
            scope=RuleScope.ROLE,
            target_role_id=r_guest.id,
            rule_type=RuleType.CHECK_ANTIPASSBACK,
            is_enabled=True
        )

        db.session.add_all([rule_demo, rule_vip_cap, rule_guest_apb])
        db.session.commit()

        # --- 6. KREIRANJE KORISNIKA I KARTICA ---
        print("👥 Kreiranje Korisnika...")

        # 1. Marko Direktor (Ima pristup svuda)
        u_director = User(first_name="Marko", last_name="Marković", role_id=r_director.id)
        db.session.add(u_director)
        db.session.commit()
        
        c_director = Credential(
            user_id=u_director.id, 
            cred_type=CredentialType.RFID, 
            cred_value="DIR-001"
        )

        # 2. Jovan Pilot (AirSerbia Zaposleni)
        u_pilot = User(
            first_name="Jovan", 
            last_name="Jovanović", 
            role_id=r_employee.id, 
            tenant_id=t_airserbia.id
        )
        db.session.add(u_pilot)
        db.session.commit()

        c_pilot_rfid = Credential(
            user_id=u_pilot.id,
            cred_type=CredentialType.RFID,
            cred_value="EMP-AIR-001"
        )
        # Jovan ima i auto (LPR)
        c_pilot_lpr = Credential(
            user_id=u_pilot.id,
            cred_type=CredentialType.LPR,
            cred_value="BG-999-AS"
        )

        # 3. Petar Putnik (Običan gost)
        u_guest = User(first_name="Petar", last_name="Petrović", role_id=r_guest.id)
        db.session.add(u_guest)
        db.session.commit()

        c_guest_qr = Credential(
            user_id=u_guest.id,
            cred_type=CredentialType.QR,
            cred_value="QR-TICKET-12345"
        )

        db.session.add_all([c_director, c_pilot_rfid, c_pilot_lpr, c_guest_qr])
        db.session.commit()

        print("✅ BAZA USPEŠNO INICIJALIZOVANA!")
        print("   - Hijerarhija: Aerodrom -> VIP Garaža")
        print("   - Test RFID (Direktor - prolazi sve): 'DIR-001'")
        print("   - Test RFID (Zaposleni - limitiran): 'EMP-AIR-001'")
        print("   - Test QR (Gost): 'QR-TICKET-12345'")

if __name__ == "__main__":
    seed_database()