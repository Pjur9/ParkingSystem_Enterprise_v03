from __future__ import annotations
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from typing import List, Tuple, Optional
from flask_socketio import SocketIO
from models import (
    db, User, Credential, Gate, Zone, ParkingSession, 
    ValidationRule, RuleType, RuleScope, ScanLog, Tenant, CredentialType
)

SCAN_CACHE = {}
CACHE_TIMEOUT_SECONDS = 20

class ParkingLogicService:
    """
    ParkingOS V3.0 Logic Engine.
    
    Centralni servis koji donosi odluke o pristupu na osnovu:
    1. Identiteta (User/Credential/Role)
    2. Konteksta (Gate/Zone Direction)
    3. Pravila iz baze (ValidationRules)
    """

    def __init__(self, socketio: SocketIO):
        self.socketio = socketio

    def handle_scan(self, gate_id: int, cred_type: str, cred_value: str) -> dict:
        """
        Glavna metoda koju poziva Forwarder kada stignu podaci sa hardvera.
        Vraća: {"allow": bool, "reason": str, ...}
        """
        now = datetime.now()

        scan_key = f"{gate_id}:{cred_value}"

        keys_to_delete = [k for k, v in SCAN_CACHE.items() if (now - v).total_seconds() > CACHE_TIMEOUT_SECONDS]
        for k in keys_to_delete:
            del SCAN_CACHE[k]

        # 2. Proveri da li je duplikat
        if scan_key in SCAN_CACHE:
            last_seen = SCAN_CACHE[scan_key]
            seconds_ago = (now - last_seen).total_seconds()
            
            if seconds_ago < CACHE_TIMEOUT_SECONDS:
                print(f"DEBOUNCE: Ignorišem dupli sken '{cred_value}' (Preostalo: {int(CACHE_TIMEOUT_SECONDS - seconds_ago)}s)")
                # Vraćamo 'ignore' rezultat da Forwarder zna da ne radi ništa
                return {
                    "allow": False, 
                    "reason": "DUPLICATE_SCAN_IGNORED"
                }

        # 3. Ako nije duplikat, upiši ga u keš i nastavi
        SCAN_CACHE[scan_key] = now
        
        # 1. PRIPREMA PODATAKA (Eager Loading za performanse)
        # Učitavamo Gate i povezane zone (from/to)
        gate = Gate.query.filter_by(id=gate_id).options(
            joinedload(Gate.zone_from),
            joinedload(Gate.zone_to)
        ).first()

        if not gate:
            return self._deny(None, None, cred_type, cred_value, "UNKNOWN_GATE")

        # Učitavamo Kredenšl -> User -> Role -> Tenant
        credential = Credential.query.filter_by(
            cred_type=cred_type, 
            cred_value=cred_value, 
            is_active=True
        ).options(
            joinedload(Credential.user).joinedload(User.role),
            joinedload(Credential.user).joinedload(User.tenant)
        ).first()

        # Scenarijo: Nepoznata kartica
        if not credential:
            self._log_scan(gate, cred_type, cred_value, False, "UNKNOWN_CREDENTIAL")
            self._emit_access_log(gate, None, None, cred_value, False, "UNKNOWN_CREDENTIAL")
            return {"allow": False, "reason": "UNKNOWN_CREDENTIAL"}

        user = credential.user
        role = user.role

        # 2. ODREĐIVANJE KONTEKSTA KRETANJA
        # entry_gate: zone_from=None, zone_to=Garage
        # exit_gate: zone_from=Garage, zone_to=None
        # internal_gate: zone_from=Garage, zone_to=VIP
       

        # 3. PRIKUPLJANJE PRAVILA (Chain of Responsibility)
        # Skupljamo sva pravila: Globalna + Zonska + Gejt + Rola
        target_zone = gate.zone_to
        source_zone = gate.zone_from
        
        # 1. Dobavi sva relevantna pravila iz baze
        rules = self._fetch_applicable_rules(gate, target_zone, role)

        # 2. Propusti kroz validator (ovo zamenjuje _check_capacity, _check_antipassback, itd.)
        is_allowed, reason = self._validate_rules(rules, user, gate, target_zone, source_zone)
        
        if not is_allowed:
            self._log_scan(gate, cred_type, cred_value, False, reason, user)
            self._emit_access_log(gate, user, credential, cred_value, False, reason)
            return {"allow": False, "reason": reason}

        # ----------------------------------------
        # 4. IZVRŠENJE TRANSAKCIJE (Side Effects)
        # ----------------------------------------
        try:
            self._execute_access_transaction(user, credential, gate, target_zone, source_zone)
            
            # Log & Emit Success
            self._log_scan(gate, cred_type, cred_value, True, "ACCESS_GRANTED", user)
            self._emit_access_log(gate, user, credential, cred_value, True, "ACCESS_GRANTED")
            
            return {
                "allow": True, 
                "reason": "ACCESS_GRANTED", 
                "user": f"{user.first_name} {user.last_name}",
                "role": role.name
            }
        except Exception as e:
            db.session.rollback()
            print(f"CRITICAL ERROR in transaction: {str(e)}")
            return {"allow": False, "reason": "SYSTEM_ERROR"}

        # 5. IZVRŠENJE TRANSAKCIJE (Side Effects)
        try:
            self._execute_access_transaction(user, credential, gate, target_zone, source_zone)
            
            # Log & Emit Success
            self._log_scan(gate, cred_type, cred_value, True, "ACCESS_GRANTED", user)
            self._emit_access_log(gate, user, credential, cred_value, True, "ACCESS_GRANTED")
            
            return {
                "allow": True, 
                "reason": "ACCESS_GRANTED", 
                "user": f"{user.first_name} {user.last_name}",
                "role": role.name
            }
        except Exception as e:
            db.session.rollback()
            print(f"CRITICAL ERROR in transaction: {str(e)}")
            return {"allow": False, "reason": "SYSTEM_ERROR"}

    def _fetch_applicable_rules(self, gate: Gate, zone: Zone, role) -> List[ValidationRule]:
        """
        Vraća listu aktivnih pravila koja se primenjuju na ovaj zahtev.
        """
        queries = []

        # A. Globalna pravila
        queries.append(ValidationRule.scope == RuleScope.GLOBAL)

        # B. Pravila Ciljne Zone (ako ulazimo negde)
        if zone:
            queries.append(
                (ValidationRule.scope == RuleScope.ZONE) & 
                (ValidationRule.target_zone_id == zone.id)
            )

        # C. Pravila Gejta
        queries.append(
            (ValidationRule.scope == RuleScope.GATE) & 
            (ValidationRule.target_gate_id == gate.id)
        )

        # D. Pravila Role (npr. Restrikcije za goste)
        if role:
            queries.append(
                (ValidationRule.scope == RuleScope.ROLE) & 
                (ValidationRule.target_role_id == role.id)
            )

        return ValidationRule.query.filter(
            or_(*queries),
            ValidationRule.is_enabled == True
        ).all()

    def _validate_rules(self, rules: List[ValidationRule], user: User, gate: Gate, target_zone: Zone, source_zone: Zone) -> Tuple[bool, str]:
        """
        Prolazi kroz listu pravila i proverava uslove.
        Ako bilo koje pravilo padne (a rola ga ne ignoriše), vraća False.
        """
        
        # Osnovna provera
        if not user.is_active:
            return False, "USER_INACTIVE"

        # Pronađi aktivnu sesiju (ako postoji)
        active_session = ParkingSession.query.filter_by(user_id=user.id, exit_time=None).first()

        for rule in rules:
            
            # --- RULE: CHECK_CAPACITY ---
            if rule.rule_type == RuleType.CHECK_CAPACITY:
                # Provera da li Rola ignoriše ovo pravilo (VIP)
                if user.role.can_ignore_capacity:
                    continue 

                # Provera kapaciteta Zone
                if target_zone:
                    if target_zone.occupancy >= target_zone.capacity:
                        return False, "ZONE_FULL"
                
                # Provera kapaciteta Tenanta (Ako je B2B korisnik)
                if user.tenant and rule.scope != RuleScope.ZONE: # Tenant limit proveravamo globalno ili na ulazu
                    if user.tenant.current_usage >= user.tenant.quota_limit:
                        return False, "TENANT_QUOTA_EXCEEDED"

            # --- RULE: CHECK_ANTIPASSBACK ---
            elif rule.rule_type == RuleType.CHECK_ANTIPASSBACK:
                if user.role.can_ignore_antipassback:
                    continue

                # ULAZ: Ako ulazi u sistem (Zone From je None), ne sme imati otvorenu sesiju
                if gate.zone_from_id is None: 
                    if active_session:
                        return False, "ALREADY_INSIDE"
                
                # IZLAZ: Ako izlazi iz sistema (Zone To je None), mora imati sesiju
                elif gate.zone_to_id is None:
                    if not active_session:
                        # Možemo dozvoliti izlaz ako je soft APB, ali za sada strogo:
                        return False, "NO_ENTRY_RECORD"

            # --- RULE: CHECK_SCHEDULE ---
            elif rule.rule_type == RuleType.CHECK_SCHEDULE:
                if user.role.can_ignore_schedule:
                    continue
                # TODO: Implementirati parsiranje JSON vremena iz rule.custom_params
                # Za sada prolazi
                pass

            # --- RULE: CHECK_PAYMENT ---
            elif rule.rule_type == RuleType.CHECK_PAYMENT:
                if not user.role.is_billable:
                    continue
                # Ovde bi išla provera da li je plaćeno
                pass

        return True, "OK"

    def _execute_access_transaction(self, user: User, credential: Credential, gate: Gate, target_zone: Zone, source_zone: Zone):
        """
        Ažurira stanje baze nakon odobrenog pristupa.
        """
        session = ParkingSession.query.filter_by(user_id=user.id, exit_time=None).first()
        now = datetime.now()

        # A. ULAZ U ZONU (Inc Occupancy)
        if target_zone:
            target_zone.occupancy += 1
            if user.tenant:
                user.tenant.current_usage += 1
            
            # Ako nema sesije (Ulaz u kompleks), kreiraj je
            if not session and gate.zone_from_id is None:
                new_session = ParkingSession(
                    user_id=user.id,
                    credential_id=credential.id,
                    entry_gate_id=gate.id,
                    entry_time=now
                )
                db.session.add(new_session)
            
            # Tranzit unutar kompleksa (Ažuriraj zonu u sesiji)
            elif session:
                session.zone_id = target_zone.id

            self._emit_occupancy_update(target_zone)

        # B. IZLAZ IZ ZONE (Dec Occupancy)
        if source_zone:
            if source_zone.occupancy > 0:
                source_zone.occupancy -= 1
            if user.tenant and user.tenant.current_usage > 0:
                user.tenant.current_usage -= 1
            
            self._emit_occupancy_update(source_zone)
            
            # Ako je ovo konačni izlaz (Napolje)
            if gate.zone_to_id is None and session:
                session.exit_time = now
                session.exit_gate_id = gate.id
                # Ovde dodajemo logiku za cenu
                session.total_cost = 0 

        credential.last_used_at = now
        db.session.commit()

    def _log_scan(self, gate, cred_type, raw_payload, granted, reason, user=None):
        """Upisuje u ScanLog tabelu."""
        try:
            # Konverzija stringa u Enum ako je potrebno
            c_type_enum = CredentialType(cred_type) if isinstance(cred_type, str) else cred_type
            
            log = ScanLog(
                gate_id=gate.id if gate else None,
                gate_name_snapshot=gate.name if gate else "UNKNOWN",
                scan_type=c_type_enum,
                raw_payload=raw_payload,
                is_access_granted=granted,
                denial_reason=reason,
                resolved_user_id=user.id if user else None,
                resolved_tenant_id=user.tenant_id if user else None
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"ERROR logging scan: {e}")
            db.session.rollback()

    def _deny(self, user, gate_id, c_type, c_val, reason):
        return {"allow": False, "reason": reason}

    # --- SOCKET.IO EMITTERS ---

    # backend/services/parking_service.py

    # backend/services/parking_service.py (kraj fajla)

    def _emit_access_log(self, gate, user, credential, raw_payload, granted, reason):
        """Šalje Live Event na Frontend"""
        payload = {
            "time": datetime.now().isoformat(),
            "gate_name": gate.name if gate else "Unknown Gate",
            "gate_id": gate.id if gate else None,
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown User",
            "role": user.role.name if user and user.role else "-",
            "credential": raw_payload,
            "status": "ALLOWED" if granted else "DENIED",
            "reason": reason,
            "is_entry": gate.zone_to_id is not None if gate else False
        }
        
        print(f"📡 EMIT: {payload['user_name']} - {payload['status']}")
        
        # POPRAVKA: Obrisano broadcast=True
        self.socketio.emit('access_log', payload, namespace='/')

    def _emit_occupancy_update(self, zone):
        """Šalje update popunjenosti zone"""
        payload = {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "current": zone.occupancy,
            "capacity": zone.capacity,
            "percent": round((zone.occupancy / zone.capacity * 100), 1) if zone.capacity > 0 else 0
        }
        
        # POPRAVKA: Obrisano broadcast=True
        self.socketio.emit('occupancy_update', payload, namespace='/')

    # --- NOVE METODE ZA VALIDACIJU (FAZA 3) ---

    def _check_capacity(self, gate, user):
        """Proverava da li ima mesta u zoni u koju se ulazi."""
        if not gate.zone_to_id:
            return True, "OK" # Izlazak napolje, ne proveravamo kapacitet

        # 1. Da li postoji aktivno pravilo za ovu zonu?
        rule = ValidationRule.query.filter_by(
            rule_type=RuleType.CHECK_CAPACITY,
            scope=RuleScope.ZONE,
            target_zone_id=gate.zone_to_id,
            is_enabled=True
        ).first()

        # Ako pravilo ne postoji ili je ugašeno, puštamo (Fail-Open)
        if not rule:
            return True, "RULE_DISABLED"

        # 2. Da li korisnik ima VIP imunitet?
        if user.role.can_ignore_capacity:
            return True, "VIP_OVERRIDE"

        # 3. Provera brojeva
        zone = Zone.query.get(gate.zone_to_id)
        if zone.occupancy >= zone.capacity:
            return False, "ZONE_FULL"
        
        return True, "OK"

    def _check_antipassback(self, gate, user):
        """Proverava redosled zona (Anti-Passback)."""
        # 1. Provera Globalnog pravila
        global_rule = ValidationRule.query.filter_by(
            rule_type=RuleType.CHECK_ANTIPASSBACK,
            scope=RuleScope.GLOBAL,
            is_enabled=True
        ).first()

        if not global_rule:
             return True, "APB_DISABLED_GLOBALLY"

        # 2. Da li korisnik ima imunitet?
        if user.role.can_ignore_antipassback:
            return True, "VIP_APB_OVERRIDE"

        # 3. Logika
        # Gde gejt očekuje da korisnik bude?
        required_zone_id = gate.zone_from_id
        
        # Gde je korisnik zapravo?
        actual_zone_id = user.current_zone_id

        # Slučaj A: Ulaz spolja (required=None), a korisnik unutra
        if required_zone_id is None and actual_zone_id is not None:
            return False, "ALREADY_INSIDE"

        # Slučaj B: Prelaz iz Zone A, a korisnik nije u Zoni A
        if required_zone_id is not None and actual_zone_id != required_zone_id:
            return False, "APB_VIOLATION_WRONG_ZONE"

        return True, "OK"