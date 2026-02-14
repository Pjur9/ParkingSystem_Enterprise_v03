from flask import Blueprint, jsonify, request
from models import db, Zone, Gate

infra_bp = Blueprint('infrastructure', __name__)

# --- ZONES CRUD ---

@infra_bp.route('/zones', methods=['GET'])
def get_zones():
    zones = Zone.query.all()
    result = []
    for z in zones:
        parent = Zone.query.get(z.parent_zone_id) if z.parent_zone_id else None
        result.append({
            "id": z.id,
            "name": z.name,
            "capacity": z.capacity,
            "occupancy": z.occupancy,
            "parent_zone_id": z.parent_zone_id,
            "parent_name": parent.name if parent else "ROOT (Main Complex)"
        })
    return jsonify(result)

@infra_bp.route('/zones', methods=['POST'])
def create_zone():
    data = request.json
    try:
        new_zone = Zone(
            name=data['name'],
            capacity=int(data['capacity']),
            parent_zone_id=data.get('parent_zone_id') or None
        )
        db.session.add(new_zone)
        db.session.commit()
        return jsonify({"message": "Zone created", "id": new_zone.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@infra_bp.route('/zones/<int:id>', methods=['PUT'])
def update_zone(id):
    """Izmena zone"""
    zone = Zone.query.get(id)
    if not zone: return jsonify({"error": "Not found"}), 404
    
    data = request.json
    try:
        zone.name = data.get('name', zone.name)
        zone.capacity = int(data.get('capacity', zone.capacity))
        # Pazimo da zona ne bude roditelj sama sebi
        pid = data.get('parent_zone_id')
        if pid and int(pid) != zone.id:
            zone.parent_zone_id = pid
        elif pid == "":
            zone.parent_zone_id = None
            
        db.session.commit()
        return jsonify({"message": "Zone updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@infra_bp.route('/zones/<int:id>', methods=['DELETE'])
def delete_zone(id):
    zone = Zone.query.get(id)
    if not zone: return jsonify({"error": "Not found"}), 404
    try:
        db.session.delete(zone)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- GATES CRUD ---

@infra_bp.route('/gates', methods=['GET'])
def get_gates():
    gates = Gate.query.all()
    result = []
    for g in gates:
        z_from = Zone.query.get(g.zone_from_id) if g.zone_from_id else None
        z_to = Zone.query.get(g.zone_to_id) if g.zone_to_id else None
        
        result.append({
            "id": g.id,
            "name": g.name,
            "zone_from_id": g.zone_from_id,
            "zone_to_id": g.zone_to_id,
            "zone_from_name": z_from.name if z_from else "WORLD (Outside)",
            "zone_to_name": z_to.name if z_to else "WORLD (Outside)",
            "is_online": True
        })
    return jsonify(result)

@infra_bp.route('/gates', methods=['POST'])
def create_gate():
    data = request.json
    try:
        new_gate = Gate(
            name=data['name'],
            zone_from_id=data.get('zone_from_id') or None,
            zone_to_id=data.get('zone_to_id') or None
        )
        db.session.add(new_gate)
        db.session.commit()
        return jsonify({"message": "Gate created", "id": new_gate.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@infra_bp.route('/gates/<int:id>', methods=['PUT'])
def update_gate(id):
    """Izmena gejta"""
    gate = Gate.query.get(id)
    if not gate: return jsonify({"error": "Not found"}), 404
    
    data = request.json
    try:
        gate.name = data.get('name', gate.name)
        gate.zone_from_id = data.get('zone_from_id') or None
        gate.zone_to_id = data.get('zone_to_id') or None
        
        db.session.commit()
        return jsonify({"message": "Gate updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@infra_bp.route('/gates/<int:id>', methods=['DELETE'])
def delete_gate(id):
    gate = Gate.query.get(id)
    if not gate: return jsonify({"error": "Not found"}), 404
    try:
        db.session.delete(gate)
        db.session.commit()
        return jsonify({"message": "Deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400