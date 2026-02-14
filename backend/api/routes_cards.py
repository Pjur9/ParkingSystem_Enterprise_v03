from flask import Blueprint, jsonify, request
from models import db, User, Credential, Role, Tenant, CredentialType
from sqlalchemy.orm import joinedload

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    """Vraća korisnike sa svim njihovim kredencijalima"""
    users = User.query.options(
        joinedload(User.role), 
        joinedload(User.tenant),
        joinedload(User.credentials)
    ).order_by(User.id.desc()).all()
    
    result = []
    for u in users:
        # Pakujemo sve kredencijale u listu
        creds = [{"id": c.id, "type": c.cred_type.value, "value": c.cred_value} for c in u.credentials]
        
        result.append({
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "full_name": f"{u.first_name} {u.last_name}",
            "role_id": u.role_id,
            "role": u.role.name if u.role else "Unknown",
            "tenant_id": u.tenant_id,
            "tenant": u.tenant.name if u.tenant else None,
            "is_active": u.is_active,
            "credentials": creds  # <-- Šaljemo celu listu
        })
    return jsonify({"users": result})

@users_bp.route('/options', methods=['GET'])
def get_options():
    """Helper za frontend select box-ove"""
    roles = Role.query.all()
    tenants = Tenant.query.all()
    return jsonify({
        "roles": [{"id": r.id, "name": r.name} for r in roles],
        "tenants": [{"id": t.id, "name": t.name} for t in tenants]
    })

@users_bp.route('/', methods=['POST'])
def create_user():
    data = request.json
    try:
        # 1. Kreiraj Korisnika
        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            role_id=data['role_id'],
            tenant_id=data.get('tenant_id') or None,
            is_active=True
        )
        db.session.add(new_user)
        db.session.flush() # Da dobijemo ID odmah

        # 2. Kreiraj Kredencijale (Loop)
        if 'credentials' in data and isinstance(data['credentials'], list):
            for cred in data['credentials']:
                if cred.get('value'): # Samo ako ima vrednost
                    c_type = CredentialType(cred['type']) # Konverzija u Enum
                    new_c = Credential(
                        user_id=new_user.id,
                        cred_type=c_type,
                        cred_value=cred['value']
                    )
                    db.session.add(new_c)

        db.session.commit()
        return jsonify({"message": "User created", "id": new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@users_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get(id)
    if not user: return jsonify({"error": "User not found"}), 404
    
    data = request.json
    try:
        # 1. Update osnovnih podataka
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.role_id = data.get('role_id', user.role_id)
        user.tenant_id = data.get('tenant_id') or None
        
        # 2. Update Kredencijala (Strategija: Obriši stare, upiši nove)
        # Ovo je najjednostavnije za implementaciju.
        if 'credentials' in data:
            # Obriši sve postojeće
            Credential.query.filter_by(user_id=user.id).delete()
            
            # Dodaj nove
            for cred in data['credentials']:
                if cred.get('value'):
                    c_type = CredentialType(cred['type'])
                    new_c = Credential(
                        user_id=user.id,
                        cred_type=c_type,
                        cred_value=cred['value']
                    )
                    db.session.add(new_c)
        
        db.session.commit()
        return jsonify({"message": "User updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)
    if not user: return jsonify({"error": "Not found"}), 404
    
    db.session.delete(user) # Cascade će obrisati i credentials
    db.session.commit()
    return jsonify({"message": "Deleted"})