from flask import Blueprint, jsonify, request
from models import db, ValidationRule, RuleType, RuleScope

rules_bp = Blueprint('rules', __name__)

@rules_bp.route('/', methods=['GET'])
def get_rules():
    # Vraća sva pravila sortirana po tipu
    rules = ValidationRule.query.order_by(ValidationRule.rule_type).all()
    result = []
    for r in rules:
        result.append({
            "id": r.id,
            "rule_type": r.rule_type.value,
            "scope": r.scope.value,
            "target_zone_id": r.target_zone_id,
            "is_enabled": r.is_enabled
        })
    return jsonify(result)

@rules_bp.route('/<int:id>/toggle', methods=['POST'])
def toggle_rule(id):
    """Pali ili gasi pravilo"""
    rule = ValidationRule.query.get(id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    
    # Obrni vrednost (True -> False, False -> True)
    rule.is_enabled = not rule.is_enabled
    db.session.commit()
    
    status = "ENABLED" if rule.is_enabled else "DISABLED"
    return jsonify({"message": f"Rule {status}", "is_enabled": rule.is_enabled})

@rules_bp.route('/init', methods=['POST'])
def init_default_rules():
    """Helper ruta za kreiranje podrazumevanih pravila ako ne postoje"""
    # 1. Globalni Anti-Passback
    if not ValidationRule.query.filter_by(rule_type=RuleType.CHECK_ANTIPASSBACK, scope=RuleScope.GLOBAL).first():
        db.session.add(ValidationRule(rule_type=RuleType.CHECK_ANTIPASSBACK, scope=RuleScope.GLOBAL, is_enabled=True))
    
    # 2. Globalni Blacklist Check
    if not ValidationRule.query.filter_by(rule_type=RuleType.CHECK_BLACKLIST, scope=RuleScope.GLOBAL).first():
        db.session.add(ValidationRule(rule_type=RuleType.CHECK_BLACKLIST, scope=RuleScope.GLOBAL, is_enabled=True))
        
    db.session.commit()
    return jsonify({"message": "Default rules initialized"})