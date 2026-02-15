from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import enum

db = SQLAlchemy()

# --- ENUMS for Type Safety ---
class CredentialType(enum.Enum):
    RFID = "RFID"
    LPR = "LPR"
    QR = "QR"
    PIN = "PIN"

class RuleScope(enum.Enum):
    GLOBAL = "GLOBAL"
    ZONE = "ZONE"
    GATE = "GATE"
    ROLE = "ROLE"

class RuleType(enum.Enum):
    CHECK_CAPACITY = "CHECK_CAPACITY"
    CHECK_SCHEDULE = "CHECK_SCHEDULE"
    CHECK_PAYMENT = "CHECK_PAYMENT"
    CHECK_ANTIPASSBACK = "CHECK_ANTIPASSBACK"
    CHECK_BLACKLIST = "CHECK_BLACKLIST"

# --- 1. IDENTITY & ACCESS (RBAC) ---

class Role(db.Model):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # e.g., "VIP", "Staff", "Guest"
    description = Column(String(200))
    
    # Granular Permissions (V3.0 Specs)
    can_ignore_capacity = Column(Boolean, default=False, nullable=False)
    can_ignore_antipassback = Column(Boolean, default=False, nullable=False)
    can_ignore_schedule = Column(Boolean, default=False, nullable=False)
    is_billable = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="role")
    rules = relationship("ValidationRule", back_populates="target_role")

class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    quota_limit = Column(Integer, default=0, nullable=False)
    current_usage = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="tenant")

class User(db.Model):
    """
    Represents the Human or System Entity.
    Separated from 'Credential' to allow multiple cards/plates per user.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    phone_number = Column(String(50), nullable=True)
    # RBAC & Tenancy
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True)

    created_at = Column(DateTime(timezone=True), default=func.now())
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")
    tenant = relationship("Tenant", back_populates="users")
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("ParkingSession", back_populates="user")

class Credential(db.Model):
    """
    Physical or Digital Access Methods (RFID Card, License Plate, etc.)
    """
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    cred_type = Column(Enum(CredentialType), nullable=False)
    cred_value = Column(String(100), unique=True, nullable=False, index=True) # The raw RFID or Plate string
    
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="credentials")

# --- 2. SPATIAL & HARDWARE ---

class Zone(db.Model):
    __tablename__ = 'zones'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    
    # Capacity Logic
    capacity = Column(Integer, default=0)
    occupancy = Column(Integer, default=0)
    
    # Hierarchy (Self-Referential)
    parent_zone_id = Column(Integer, ForeignKey('zones.id', ondelete='CASCADE'), nullable=True)
    
    children = relationship("Zone", 
                            backref=backref('parent', remote_side=[id]),
                            cascade="all, delete-orphan")
    
    # Rules targeting this zone
    rules = relationship("ValidationRule", back_populates="target_zone")

class Gate(db.Model):
    __tablename__ = 'gates'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    
    # Directional Logic (Essential for V3.0)
    # entry_gate: zone_from=None, zone_to=Garage
    # exit_gate: zone_from=Garage, zone_to=None
    # internal_gate: zone_from=Garage, zone_to=VIP_Area
    zone_from_id = Column(Integer, ForeignKey('zones.id'), nullable=True)
    zone_to_id = Column(Integer, ForeignKey('zones.id'), nullable=True)

    is_active = Column(Boolean, default=True)

    zone_from = relationship("Zone", foreign_keys=[zone_from_id])
    zone_to = relationship("Zone", foreign_keys=[zone_to_id])
    
    devices = relationship("Device", back_populates="gate", cascade="all, delete-orphan")
    rules = relationship("ValidationRule", back_populates="target_gate")

class Device(db.Model):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    ip_address = Column(String(50), nullable=False)
    port = Column(Integer, default=5005)
    
    device_type = Column(String(20)) # Camera, Controller
    config = Column(Text, nullable=True) # JSON config for specific hardware parameters

    gate_id = Column(Integer, ForeignKey('gates.id', ondelete='CASCADE'), nullable=False)
    gate = relationship("Gate", back_populates="devices")

# --- 3. LOGIC CONFIGURATION (The "Brain") ---

class ValidationRule(db.Model):
    """
    Configuration-Driven Logic Engine.
    Replaces hardcoded checks.
    """
    __tablename__ = 'validation_rules'

    id = Column(Integer, primary_key=True)
    
    # What level is this rule applied at?
    scope = Column(Enum(RuleScope), nullable=False) # GLOBAL, ZONE, GATE, ROLE
    
    # The actual Logic Type
    rule_type = Column(Enum(RuleType), nullable=False) 
    
    # Polymorphic Targets (Only one should be set based on scope)
    target_zone_id = Column(Integer, ForeignKey('zones.id', ondelete='CASCADE'), nullable=True)
    target_gate_id = Column(Integer, ForeignKey('gates.id', ondelete='CASCADE'), nullable=True)
    target_role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=True)

    # Configuration
    is_enabled = Column(Boolean, default=True, nullable=False)
    custom_params = Column(Text, nullable=True) # JSON for extra params (e.g. {"start_time": "08:00"})

    # Relationships
    target_zone = relationship("Zone", back_populates="rules")
    target_gate = relationship("Gate", back_populates="rules")
    target_role = relationship("Role", back_populates="rules")

# --- 4. OPERATIONAL DATA ---

class ParkingSession(db.Model):
    __tablename__ = 'parking_sessions'

    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    credential_id = Column(Integer, ForeignKey('credentials.id'), nullable=False)
    
    entry_gate_id = Column(Integer, ForeignKey('gates.id'), nullable=False)
    entry_time = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    exit_gate_id = Column(Integer, ForeignKey('gates.id'), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)

    # Derived Data for Analysis
    total_cost = Column(Integer, default=0) # In cents
    
    user = relationship("User", back_populates="sessions")
    entry_gate = relationship("Gate", foreign_keys=[entry_gate_id])
    exit_gate = relationship("Gate", foreign_keys=[exit_gate_id])

# --- 5. LOGGING & AUDIT (The "Black Box") ---

class ScanLog(db.Model):
    """
    Immutabilni log svih događaja na kapijama.
    Beleži sirove podatke, čak i ako je pristup odbijen ili korisnik nepoznat.
    """
    __tablename__ = 'scan_logs'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Gde se desilo?
    gate_id = Column(Integer, ForeignKey('gates.id', ondelete='SET NULL'), nullable=True, index=True)
    gate_name_snapshot = Column(String(50)) # Čuvamo ime gate-a u trenutku skeniranja (u slučaju da se gate obriše)

    # Šta je skenirano? (Sirovi podaci)
    scan_type = Column(Enum(CredentialType), nullable=False) # RFID, LPR, QR
    raw_payload = Column(String(100), nullable=False, index=True) # Npr. "E2801160..." ili "BG-123-AA"

    # Ishod Logike (Decision Engine Result)
    is_access_granted = Column(Boolean, nullable=False)
    denial_reason = Column(String(255), nullable=True) # Npr. "ZONE_FULL", "CARD_EXPIRED", "ANTIPASSBACK_VIOLATION"

    # Ako smo uspeli da identifikujemo korisnika (Optional Link)
    resolved_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True)

    # Relacije (samo za čitanje)
    gate = relationship("Gate")
    resolved_user = relationship("User")

    def __repr__(self):
        status = "ALLOWED" if self.is_access_granted else f"DENIED ({self.denial_reason})"
        return f"<ScanLog {self.raw_payload} @ {self.gate_name_snapshot} -> {status}>"