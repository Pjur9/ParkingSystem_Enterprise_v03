from flask import Blueprint, jsonify, request
from models import db, Role

roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/', methods=['GET'])
def get_roles():
    roles = Role.query.all()
    result = []
    for r in roles:
        result.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "can_ignore_capacity": r.can_ignore_capacity,
            "can_ignore_antipassback": r.can_ignore_antipassback,
            "is_billable": r.is_billable
        })
    return jsonify(result)

@roles_bp.route('/', methods=['POST'])
def create_role():
    data = request.json
    try:
        new_role = Role(
            name=data['name'],
            description=data.get('description', ''),
            can_ignore_capacity=data.get('can_ignore_capacity', False),
            can_ignore_antipassback=data.get('can_ignore_antipassback', False),
            is_billable=data.get('is_billable', False)
        )
        db.session.add(new_role)
        db.session.commit()
        return jsonify({"message": "Role created", "id": new_role.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@roles_bp.route('/<int:id>', methods=['PUT'])
def update_role(id):
    role = Role.query.get(id)
    if not role: return jsonify({"error": "Role not found"}), 404
    
    data = request.json
    try:
        role.name = data.get('name', role.name)
        role.description = data.get('description', role.description)
        role.can_ignore_capacity = data.get('can_ignore_capacity', role.can_ignore_capacity)
        role.can_ignore_antipassback = data.get('can_ignore_antipassback', role.can_ignore_antipassback)
        role.is_billable = data.get('is_billable', role.is_billable)
        
        db.session.commit()
        return jsonify({"message": "Role updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@roles_bp.route('/<int:id>', methods=['DELETE'])
def delete_role(id):
    role = Role.query.get(id)
    if not role: return jsonify({"error": "Role not found"}), 404
    try:
        db.session.delete(role)
        db.session.commit()
        return jsonify({"message": "Role deleted"})
    except Exception as e:
        return jsonify({"error": "Cannot delete role (maybe assigned to users?)"}), 400