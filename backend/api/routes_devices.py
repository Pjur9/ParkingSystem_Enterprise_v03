from flask import Blueprint, jsonify, request
from models import db, Device, Gate
from sqlalchemy.exc import IntegrityError

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/', methods=['GET'])
def get_devices():
    """Vraća listu svih fizičkih uređaja"""
    devices = Device.query.all()
    result = []
    
    for d in devices:
        # Dohvati ime gejta ako je povezan
        gate_name = "Unassigned"
        if d.gate_id:
            gate = Gate.query.get(d.gate_id)
            if gate: gate_name = gate.name

        result.append({
            "id": d.id,
            "name": d.name if hasattr(d, 'name') else f"Device {d.id}", # Ako nemas 'name' kolonu, koristi ID
            "ip_address": d.ip_address,
            "port": d.port,
            "device_type": d.device_type.value if hasattr(d.device_type, 'value') else str(d.device_type),
            "gate_id": d.gate_id,
            "gate_name": gate_name
        })
    return jsonify(result)

@devices_bp.route('/options', methods=['GET'])
def get_options():
    """Vraća listu Gejtova za dropdown"""
    gates = Gate.query.all()
    return jsonify({
        "gates": [{"id": g.id, "name": g.name} for g in gates]
    })

@devices_bp.route('/', methods=['POST'])
def create_device():
    data = request.json
    try:
        new_device = Device(
            name=data.get('name', 'New Device'),
            ip_address=data['ip_address'],
            port=int(data.get('port', 80)),
            device_type=data['device_type'], # Očekujemo string: "LPR_CAMERA", "CONTROLLER"...
            gate_id=int(data['gate_id']) if data.get('gate_id') else None
        )
        db.session.add(new_device)
        db.session.commit()
        return jsonify({"message": "Device added", "id": new_device.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "IP Address already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@devices_bp.route('/<int:id>', methods=['PUT'])
def update_device(id):
    device = Device.query.get(id)
    if not device: return jsonify({"error": "Not found"}), 404
    
    data = request.json
    try:
        device.name = data.get('name', device.name)
        device.ip_address = data.get('ip_address', device.ip_address)
        device.port = int(data.get('port', device.port))
        device.device_type = data.get('device_type', device.device_type)
        device.gate_id = int(data['gate_id']) if data.get('gate_id') else None
        
        db.session.commit()
        return jsonify({"message": "Device updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@devices_bp.route('/<int:id>', methods=['DELETE'])
def delete_device(id):
    device = Device.query.get(id)
    if not device: return jsonify({"error": "Not found"}), 404
    
    db.session.delete(device)
    db.session.commit()
    return jsonify({"message": "Device deleted"})