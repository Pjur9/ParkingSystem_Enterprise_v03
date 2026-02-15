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
    Centralni servis za odluke o pristupu.
    """

    def __init__(self, socketio: SocketIO):
        self.socketio = socketio

    def handle_scan(self, gate_id: int, cred_type: str, cred_value: str) -> dict:
        """
        Glavna metoda koju poziva Forwarder.
        """
        now = datetime.now()

        # --- 1. DEBOUNCE ZAŠTITA ---
        scan_key = f"{gate_id}:{cred_value}"
        
        # Očisti stari keš
        keys_to_delete = [k for k, v in SCAN_CACHE.items() if (now - v).total_seconds() > CACHE_TIMEOUT_SECONDS]
        for k in keys_to_delete:
            del SCAN_CACHE[k]

        # Proveri duplikat
        if scan_key in SCAN_CACHE:
            last_seen = SCAN_CACHE[scan_key]
            seconds_ago = (now - last_seen).total_seconds()
            
            if seconds_ago < CACHE_TIMEOUT_SECONDS:
                print(f"DEBOUNCE: Ignorišem dupli sken '{cred_value}' (Preostalo: {int(CACHE_TIMEOUT_SECONDS - seconds_ago)}s)")
                return {"allow": False, "reason": "DUPLICATE_SCAN_IGNORED"}

        SCAN_CACHE[scan_key] = now
        
        # --- 2. UČITAVANJE PODATAKA ---
        gate = Gate.query.filter_by(id=gate_id).options(
            joinedload(Gate.zone_from),
            joinedload(Gate.zone_to)
        ).first()

        if not gate:
            return self._deny(None, None, cred_type, cred_value, "UNKNOWN_GATE")
        
        target_zone = gate.zone_to
        if target_zone:
            # Ponovo učitavamo zonu sa LOCK-om. Ovo blokira sve ostale dok ne završimo.
            target_zone = Zone.query.with_for_update().filter_by(id=target_zone.id).first()
        
        source_zone = gate.zone_from
        if source_zone:
             source_zone = Zone.query.with_for_update().filter_by(id=source_zone.id).first()
        # 🔥🔥🔥 KRAJ FIX-A 🔥🔥🔥

        credential = Credential.query.filter_by(
            cred_type=cred_type, 
            cred_value=cred_value, 
            is_active=True
        ).options(
            joinedload(Credential.user).joinedload(User.role),
            joinedload(Credential.user).joinedload(User.tenant)
        ).first()

        if not credential:
            self._log_scan(gate, cred_type, cred_value, False, "UNKNOWN_CREDENTIAL")
            self._emit_access_log(gate, None, None, cred_value, False, "UNKNOWN_CREDENTIAL")
            return {"allow": False, "reason": "UNKNOWN_CREDENTIAL"}

        user = credential.user
        role = user.role
        target_zone = gate.zone_to
        source_zone = gate.zone_from

        # --- 3. VALIDACIJA PRAVILA ---
        rules = self._fetch_applicable_rules(gate, target_zone, role)
        
        # Pronađi aktivnu sesiju (Gde je korisnik SADA?)
        # Ovo je ključno za APB. Ako ima sesiju, unutra je.
        active_session = ParkingSession.query.filter_by(user_id=user.id, exit_time=None).first()

        is_allowed, reason = self._validate_rules(rules, user, gate, target_zone, source_zone, active_session)
        
        if not is_allowed:
            self._log_scan(gate, cred_type, cred_value, False, reason, user)
            self._emit_access_log(gate, user, credential, cred_value, False, reason)
            return {"allow": False, "reason": reason}

        # --- 4. IZVRŠENJE ---
        try:
            self._execute_access_transaction(user, credential, gate, target_zone, source_zone, active_session)
            
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
        """Skuplja sva pravila (Global, Zone, Gate, Role)."""
        queries = []
        queries.append(ValidationRule.scope == RuleScope.GLOBAL)

        if zone:
            queries.append((ValidationRule.scope == RuleScope.ZONE) & (ValidationRule.target_zone_id == zone.id))

        queries.append((ValidationRule.scope == RuleScope.GATE) & (ValidationRule.target_gate_id == gate.id))

        if role:
            queries.append((ValidationRule.scope == RuleScope.ROLE) & (ValidationRule.target_role_id == role.id))

        return ValidationRule.query.filter(or_(*queries), ValidationRule.is_enabled == True).all()

    def _validate_rules(self, rules: List[ValidationRule], user: User, gate: Gate, target_zone: Zone, source_zone: Zone, active_session: ParkingSession) -> Tuple[bool, str]:
        """Proverava uslove."""
        
        if not user.is_active:
            return False, "USER_INACTIVE"

        for rule in rules:
            
            # --- CAPACITY CHECK ---
            if rule.rule_type == RuleType.CHECK_CAPACITY:
                if user.role.can_ignore_capacity: continue 

                if target_zone and target_zone.occupancy >= target_zone.capacity:
                    return False, "ZONE_FULL"
                
                if user.tenant and rule.scope != RuleScope.ZONE:
                    if user.tenant.current_usage >= user.tenant.quota_limit:
                        return False, "TENANT_QUOTA_EXCEEDED"

            # --- ANTIPASSBACK CHECK ---
            elif rule.rule_type == RuleType.CHECK_ANTIPASSBACK:
                if user.role.can_ignore_antipassback: continue

                # ULAZ (Zone From = None): Korisnik ne sme biti unutra (imati sesiju)
                if gate.zone_from_id is None: 
                    if active_session:
                        return False, "ALREADY_INSIDE"
                
                # IZLAZ (Zone To = None): Korisnik mora biti unutra
                elif gate.zone_to_id is None:
                    if not active_session:
                        return False, "NO_ENTRY_RECORD"
                
                # TRANZIT (Iz Zone A u Zonu B): Mora biti u Zoni A
                else:
                    if not active_session or active_session.zone_id != gate.zone_from_id:
                        # Strogi APB: Moraš biti tačno u zoni iz koje dolaziš
                        return False, "APB_VIOLATION_WRONG_ZONE"

            # --- SCHEDULE CHECK ---
            elif rule.rule_type == RuleType.CHECK_SCHEDULE:
                if user.role.can_ignore_schedule: continue
                # TODO: Implementirati proveru vremena
                pass

            # --- PAYMENT CHECK ---
            elif rule.rule_type == RuleType.CHECK_PAYMENT:
                if not user.role.is_billable: continue
                # TODO: Provera plaćanja
                pass

        return True, "OK"

    def _execute_access_transaction(self, user: User, credential: Credential, gate: Gate, target_zone: Zone, source_zone: Zone, session: ParkingSession):
        """Ažurira bazu."""
        now = datetime.now()

        # A. ULAZ U ZONU
        if target_zone:
            target_zone.occupancy += 1
            if user.tenant: user.tenant.current_usage += 1
            
            # Ako nema sesije (Ulaz u kompleks), kreiraj je
            if not session and gate.zone_from_id is None:
                new_session = ParkingSession(
                    user_id=user.id,
                    credential_id=credential.id,
                    entry_gate_id=gate.id,
                    entry_time=now
                )
                db.session.add(new_session)
            
            # Tranzit (Ažuriraj zonu)
            elif session:
                session.zone_id = target_zone.id

            self._emit_occupancy_update(target_zone)

        # B. IZLAZ IZ ZONE
        if source_zone:
            if source_zone.occupancy > 0: source_zone.occupancy -= 1
            if user.tenant and user.tenant.current_usage > 0: user.tenant.current_usage -= 1
            
            self._emit_occupancy_update(source_zone)
            
            # KONAČNI IZLAZ (Zatvaranje sesije)
            if gate.zone_to_id is None and session:
                session.exit_time = now
                session.exit_gate_id = gate.id
                session.total_cost = 0 # TODO: Billing Logic here

        credential.last_used_at = now
        db.session.commit()

    def _log_scan(self, gate, cred_type, raw_payload, granted, reason, user=None):
        try:
            c_type_enum = CredentialType(cred_type) if isinstance(cred_type, str) else cred_type
            log = ScanLog(
                gate_id=gate.id if gate else None,
                gate_name_snapshot=gate.name if gate else "UNKNOWN",
                scan_type=c_type_enum,
                raw_payload=raw_payload,
                is_access_granted=granted,
                denial_reason=reason,
                resolved_user_id=user.id if user else None,
                resolved_tenant_id=user.tenant_id if user and user.tenant_id else None
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"ERROR logging scan: {e}")
            db.session.rollback()

    def _deny(self, user, gate_id, c_type, c_val, reason):
        return {"allow": False, "reason": reason}

    def _emit_access_log(self, gate, user, credential, raw_payload, granted, reason):
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
        if self.socketio:
            self.socketio.emit('access_log', payload, namespace='/')

    def _emit_occupancy_update(self, zone):
        payload = {
            "zone_id": zone.id,
            "zone_name": zone.name,
            "current": zone.occupancy,
            "capacity": zone.capacity,
            "percent": round((zone.occupancy / zone.capacity * 100), 1) if zone.capacity > 0 else 0
        }
        if self.socketio:
            self.socketio.emit('occupancy_update', payload, namespace='/')