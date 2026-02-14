from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.orm import joinedload
from models import db, Gate, Zone, ValidationRule, Device, ScanLog, RuleScope

gates_bp = Blueprint('gates', __name__)

# --- HELPER: JSON Serializer za Datetime ---
def serialize_log(log):
    return {
        'id': log.id,
        'scan_time': log.created_at.isoformat() if log.created_at else None,
        'gate_name': log.gate_name_snapshot,
        'scan_type': log.scan_type.value if hasattr(log.scan_type, 'value') else str(log.scan_type),
        'status': 'ALLOWED' if log.is_access_granted else 'DENIED',
        'reason': log.denial_reason,
        'user': f"{log.resolved_user.first_name} {log.resolved_user.last_name}" if log.resolved_user else "Unknown"
    }

# --- ENDPOINTS ---

@gates_bp.route('/', methods=['GET'])
def get_gates():
    """
    Vraća listu rampi obogaćenu podacima o Zoni i Aktivnim Pravilima.
    Frontendu ovo treba da bi znao da li da prikaže 'Capacity Check Active' ikonicu.
    """
    gates = Gate.query.options(joinedload(Gate.zone_to), joinedload(Gate.zone_from)).all()
    results = []
    
    for gate in gates:
        # 1. Pronađi aktivna pravila specifična za ovu rampu
        active_rules = ValidationRule.query.filter_by(
            scope=RuleScope.GATE, 
            target_gate_id=gate.id, 
            is_enabled=True
        ).all()

        rule_names = [r.rule_type.value for r in active_rules]

        # 2. Status uređaja (Simulacija - u realnosti proveravamo ping)
        # Ovde bi smo pitali Device tabelu ili Cache
        is_online = True 

        results.append({
            'id': gate.id,
            'name': gate.name,
            'direction': {
                'from': gate.zone_from.name if gate.zone_from else "EXIT (World)",
                'to': gate.zone_to.name if gate.zone_to else "ENTRY (World)"
            },
            'active_rules': rule_names, # Frontend može da crta ikone na osnovu ovoga
            'is_online': is_online
        })
    
    return jsonify(results)

@gates_bp.route('/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """
    Vraća 'Big Picture' podatke za Dashboard.
    1. Hijerarhiju Zona (Tree Structure) sa popunjenošću.
    2. Status Hardvera (Total vs Online).
    """
    
    # 1. Rekurzivna funkcija za izgradnju stabla zona
    def build_zone_tree(zone):
        children = Zone.query.filter_by(parent_zone_id=zone.id).all()
        return {
            'id': zone.id,
            'name': zone.name,
            'capacity': zone.capacity,
            'occupancy': zone.occupancy,
            'percent_full': round((zone.occupancy / zone.capacity * 100), 1) if zone.capacity > 0 else 0,
            'children': [build_zone_tree(child) for child in children]
        }

    # Krećemo od Root zona (onih koje nemaju roditelja)
    root_zones = Zone.query.filter_by(parent_zone_id=None).all()
    zone_tree = [build_zone_tree(z) for z in root_zones]

    # 2. Statistika Uređaja
    total_devices = Device.query.count()
    # Ovde bi išla logika za proveru 'last_seen'
    online_devices = Device.query.count() # Placeholder za demo

    return jsonify({
        'zones_tree': zone_tree,
        'hardware': {
            'total': total_devices,
            'online': online_devices,
            'status': 'HEALTHY' if total_devices == online_devices else 'WARNING'
        }
    })

@gates_bp.route('/logs', methods=['GET'])
def get_recent_logs():
    """Live Feed skeniranja za Dashboard"""
    logs = ScanLog.query.options(joinedload(ScanLog.resolved_user))\
        .order_by(ScanLog.created_at.desc())\
        .limit(20).all()
    
    return jsonify([serialize_log(log) for log in logs])

@gates_bp.route('/<int:gate_id>/open', methods=['POST'])
def open_gate_manual(gate_id):
    """Ručno otvaranje (Admin Override)"""
    # Ovde bi pozvali forwarder servis
    # forwarder.send_open_command(gate_id)
    return jsonify({'status': 'success', 'message': f'Command sent to Gate {gate_id}'})