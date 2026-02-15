# backend/tests/test_logic_matrix.py
import pytest
import sys
import os
import random
from datetime import datetime

# Dodajemo putanju do aplikacije
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Zone, Gate, Tenant, Credential, ParkingSession, Role, ValidationRule, RuleScope, RuleType
from services.parking_service import ParkingLogicService

# --- FIXTURES ---

@pytest.fixture(scope='module')
def test_app():
    app, socketio = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # RAM baza
    
    with app.app_context():
        db.create_all()
        yield app, socketio
        db.drop_all()

@pytest.fixture
def service(test_app):
    app, socketio = test_app
    svc = ParkingLogicService(socketio)
    # Resetujemo globalni keš u servisu
    import services.parking_service
    services.parking_service.SCAN_CACHE = {} 
    return svc

@pytest.fixture
def db_session(test_app):
    app, _ = test_app
    with app.app_context():
        # Clean slate pre svakog testa
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield db.session

# --- HELPER ZA KREIRANJE SCENARIJA ---

def create_scenario(session, role_name="Guest", zone_cap=10, zone_occ=0, user_inside=False, tenant_quota=None, tenant_usage=0):
    
    # 1. Rola
    role = Role(name=role_name)
    if role_name == "VIP":
        role.can_ignore_capacity = True
        role.can_ignore_antipassback = True
    elif role_name == "Staff":
        role.can_ignore_antipassback = True
    session.add(role)
    session.commit()

    # 2. Tenant
    tenant = None
    if tenant_quota is not None:
        tenant = Tenant(name="Test Corp", quota_limit=tenant_quota, current_usage=tenant_usage)
        session.add(tenant)
        session.commit()

    # 3. User
    user = User(first_name="Test", last_name="User", role_id=role.id, tenant_id=tenant.id if tenant else None, is_active=True)
    session.add(user)
    session.commit()

    # 4. Credential
    import random
    unique_tag = f"TAG_{random.randint(10000, 99999)}_{datetime.now().timestamp()}"
    cred = Credential(user_id=user.id, cred_type="RFID", cred_value=unique_tag, is_active=True)
    session.add(cred)
    session.commit()

    # 5. Zona i Gate
    zone = Zone(name="Test Zone", capacity=zone_cap, occupancy=zone_occ)
    session.add(zone)
    session.commit()

    gate = Gate(name="Entry Gate", zone_to_id=zone.id, zone_from_id=None)
    session.add(gate)
    session.commit()

    # 6. Sesija (Ako je unutra)
    if user_inside:
        parking_session = ParkingSession(
            user_id=user.id, 
            credential_id=cred.id, 
            entry_gate_id=gate.id, 
            entry_time=datetime.now()
        )
        session.add(parking_session)
        session.commit()

    # --- 7. PRAVILA (OVO JE FALILO!) ---
    # Moramo reći sistemu DA PROVERAVA pravila, inače je sve dozvoljeno.
    
    # Pravilo: Proveri Kapacitet (Globalno)
    r1 = ValidationRule(rule_type=RuleType.CHECK_CAPACITY, scope=RuleScope.GLOBAL, is_enabled=True)
    session.add(r1)

    # Pravilo: Proveri APB (Globalno)
    r2 = ValidationRule(rule_type=RuleType.CHECK_ANTIPASSBACK, scope=RuleScope.GLOBAL, is_enabled=True)
    session.add(r2)

    session.commit()

    return gate.id, unique_tag
# --- TEST CASES ---

SCENARIOS = [
    # --- GRUPA 1: OSNOVNI HAPPY PATH & KAPACITET (GUEST) ---
    # (Role, ZoneCap, ZoneOcc, IsInside, TenantQuota, TenantUsage, EXPECTED_ALLOW, EXPECTED_REASON)
    ("Guest", 10, 0, False, None, 0, True, "ACCESS_GRANTED"),          # 01. Prazna garaža
    ("Guest", 10, 5, False, None, 0, True, "ACCESS_GRANTED"),          # 02. Polupuna
    ("Guest", 10, 9, False, None, 0, True, "ACCESS_GRANTED"),          # 03. Ima još JEDNO mesto (Edge Case)
    ("Guest", 10, 10, False, None, 0, False, "ZONE_FULL"),             # 04. Puna garaža
    ("Guest", 10, 11, False, None, 0, False, "ZONE_FULL"),             # 05. Prepunjena (Overflow state)
    ("Guest", 0, 0, False, None, 0, False, "ZONE_FULL"),               # 06. Zatvorena garaža (Cap=0)

    # --- GRUPA 2: TENANT QUOTA LOGIKA (FIRME) ---
    ("Guest", 100, 0, False, 10, 0, True, "ACCESS_GRANTED"),           # 07. Tenant prazan
    ("Guest", 100, 0, False, 10, 9, True, "ACCESS_GRANTED"),           # 08. Tenant ima još 1 mesto
    ("Guest", 100, 0, False, 10, 10, False, "TENANT_QUOTA_EXCEEDED"),  # 09. Tenant pun
    ("Guest", 100, 0, False, 10, 15, False, "TENANT_QUOTA_EXCEEDED"),  # 10. Tenant prepunjen
    ("Guest", 100, 0, False, 0, 0, False, "TENANT_QUOTA_EXCEEDED"),    # 11. Tenant blokiran (Quota=0)

    # --- GRUPA 3: KONFLIKT ZONA vs TENANT (Fizika vs Ugovor) ---
    # Logika: Zone Capacity se uvek proverava PRVI. Džaba ti rezervacija ako fizički nema mesta.
    ("Guest", 10, 10, False, 5, 0, False, "ZONE_FULL"),                # 12. Zona puna, Tenant prazan -> ODBIJEN (Prioritet Zone)
    ("Guest", 10, 0, False, 5, 5, False, "TENANT_QUOTA_EXCEEDED"),     # 13. Zona prazna, Tenant pun -> ODBIJEN (Prioritet Tenanta)
    ("Guest", 10, 10, False, 5, 5, False, "ZONE_FULL"),                # 14. Oboje puno -> ODBIJEN (Vraća prvu grešku: Zona)

    # --- GRUPA 4: ANTI-PASSBACK (APB) ---
    ("Guest", 100, 0, True, None, 0, False, "ALREADY_INSIDE"),         # 15. Gost proba ući dvaput
    ("Guest", 100, 0, False, None, 0, True, "ACCESS_GRANTED"),         # 16. Gost ulazi prvi put (nije unutra)

    # --- GRUPA 5: REDOSLED PROVERA (ORDER OF OPERATIONS) ---
    # Šta ako je korisnik unutra (APB) I zona je puna?
    # Tvoj kod: 1. Capacity, 2. APB. Očekujemo ZONE_FULL.
    ("Guest", 10, 10, True, None, 0, False, "ZONE_FULL"),              # 17. Unutra je + Puno je -> Greška: ZONE_FULL
    ("Guest", 10, 5, True, None, 0, False, "ALREADY_INSIDE"),          # 18. Unutra je + Ima mesta -> Greška: ALREADY_INSIDE
    ("Guest", 10, 10, True, 5, 5, False, "ZONE_FULL"),                 # 19. Unutra + Zona Puna + Tenant Pun -> ZONE_FULL (Prvi check)

    # --- GRUPA 6: VIP KORISNIK (THE GOD MODE) ---
    # VIP u tvojoj konfiguraciji ignoriše SVE (Capacity + APB).
    ("VIP", 10, 0, False, None, 0, True, "ACCESS_GRANTED"),            # 20. Normalan ulaz
    ("VIP", 10, 10, False, None, 0, True, "ACCESS_GRANTED"),           # 21. Ignoriše punu zonu
    ("VIP", 0, 0, False, None, 0, True, "ACCESS_GRANTED"),             # 22. Ignoriše zatvorenu zonu
    ("VIP", 100, 0, False, 5, 5, True, "ACCESS_GRANTED"),              # 23. Ignoriše pun Tenant
    ("VIP", 10, 10, False, 5, 5, True, "ACCESS_GRANTED"),              # 24. Ignoriše sve puno (Zona + Tenant)
    ("VIP", 10, 5, True, None, 0, True, "ACCESS_GRANTED"),             # 25. Ignoriše APB (Ulazi dok je unutra)
    ("VIP", 10, 10, True, None, 0, True, "ACCESS_GRANTED"),            # 26. Ignoriše Puno + APB zajedno

    # --- GRUPA 7: STAFF KORISNIK (ZAPOSLENI) ---
    # Staff u setupu: Ignoriše APB, ali NE ignoriše Kapacitet.
    ("Staff", 10, 5, True, None, 0, True, "ACCESS_GRANTED"),           # 27. Staff ignoriše APB (Zaboravio karticu, ušao opet)
    ("Staff", 10, 10, False, None, 0, False, "ZONE_FULL"),             # 28. Staff poštuje Zonu (Nema mesta ni za radnike)
    ("Staff", 10, 10, True, None, 0, False, "ZONE_FULL"),              # 29. Staff unutra + Puno -> Odbijen zbog ZONE (ne APB)
    ("Staff", 100, 0, False, 5, 5, False, "TENANT_QUOTA_EXCEEDED"),    # 30. Staff poštuje kvotu svoje firme

    # --- GRUPA 8: EKSTREMNI SLUČAJEVI (MATH & LOGIC) ---
    ("Guest", 1, 0, False, None, 0, True, "ACCESS_GRANTED"),           # 31. Mikro garaža (1 mesto), prazna
    ("Guest", 1, 1, False, None, 0, False, "ZONE_FULL"),               # 32. Mikro garaža, puna
    ("Guest", 1000, 999, False, None, 0, True, "ACCESS_GRANTED"),      # 33. Veliki brojevi - OK
    ("Staff", 1, 0, True, None, 0, True, "ACCESS_GRANTED"),            # 34. Staff u mikro garaži sa APB problemom -> OK
    
    # --- GRUPA 9: MULTI-TENANT MIX ---
    # Tenant ima mesta, ali Zona je puna zbog "Javnih" korisnika
    ("Guest", 10, 10, False, 100, 1, False, "ZONE_FULL"),              # 35. Tenant prazan, ali garaža puna -> Odbijen
    ("VIP", 10, 10, False, 100, 1, True, "ACCESS_GRANTED"),            # 36. VIP prolazi i ovde

    # --- GRUPA 10: TRICKY CASES ---
    ("Guest", 5, 4, False, 2, 2, False, "TENANT_QUOTA_EXCEEDED"),      # 37. Zona ima mesta, Tenant nema
    ("Guest", 5, 5, False, 2, 1, False, "ZONE_FULL"),                  # 38. Tenant ima mesta, Zona nema
    ("Staff", 5, 5, True, 2, 1, False, "ZONE_FULL"),                   # 39. Staff (APB ignore) ali Zona puna -> Odbijen
    ("VIP", 5, 5, True, 2, 2, True, "ACCESS_GRANTED")                  # 40. VIP prolazi kroz zidove
]
@pytest.mark.parametrize("role, z_cap, z_occ, is_in, t_quota, t_use, exp_allow, exp_reason", SCENARIOS)
def test_access_matrix(test_app, service, db_session, role, z_cap, z_occ, is_in, t_quota, t_use, exp_allow, exp_reason):
    app, _ = test_app
    with app.app_context():
        # Setup
        gate_id, cred_val = create_scenario(
            db_session, 
            role_name=role, 
            zone_cap=z_cap, 
            zone_occ=z_occ, 
            user_inside=is_in, 
            tenant_quota=t_quota, 
            tenant_usage=t_use
        )

        # Action
        result = service.handle_scan(gate_id, "RFID", cred_val)

        print(f"\nScenario: Role={role}, Zone={z_occ}/{z_cap}, Inside={is_in} -> Got: {result['reason']}")
        
        # Assert
        assert result['allow'] == exp_allow, f"Expected Allow={exp_allow}, got {result['allow']} (Reason: {result['reason']})"
        
        if not exp_allow:
            assert result['reason'] == exp_reason, f"Expected Reason={exp_reason}, got {result['reason']}"