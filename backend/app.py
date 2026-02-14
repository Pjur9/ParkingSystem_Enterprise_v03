import os
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Importovanje modela i baze
from models import db

# Importovanje servisa
from services.forwarder_tcp import ForwarderIngressServer

# Importovanje API ruta (Blueprints)
# Pretpostavljamo da su fajlovi u folderu /api/
from api.routes_gates import gates_bp
from api.routes_cards import users_bp
from api.routes_infrastructure import infra_bp
from api.routes_roles import roles_bp
from api.routes_rules import rules_bp
from api.routes_devices import devices_bp
# Učitavanje Environment varijabli
load_dotenv()

# --- KONFIGURACIJA LOGOVANJA ---
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(level=logging.INFO)
file_handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, 'parking_os.log'), when="midnight", interval=1, backupCount=7
)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.getLogger().addHandler(file_handler)
logger = logging.getLogger("app")

def create_app():
    """Factory funkcija za kreiranje aplikacije"""
    app = Flask(__name__)

    # 1. Konfiguracija
    #app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_change_me')
    # Koristimo SQLite za dev, PostgreSQL za prod
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///parking_v3.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Inicijalizacija Ekstenzija
    db.init_app(app)
    CORS(app) # Dozvoli Frontend-u (Next.js) da zove API

    # 3. Inicijalizacija Socket.IO
    # async_mode='threading' je ključan jer koristimo standardne threadove za TCP server
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    # 4. Registracija API Ruta (Blueprints)
    app.register_blueprint(gates_bp, url_prefix='/api/gates')
    app.register_blueprint(users_bp, url_prefix='/api/users') # V3.0: Users umesto Cards
    app.register_blueprint(infra_bp, url_prefix='/api/infra')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')
    app.register_blueprint(rules_bp, url_prefix='/api/rules')
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
    # 5. Global Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy", "version": "3.0.0"})

    return app, socketio

# --- ENTRY POINT ---

app, socketio = create_app()

# Globalna instanca forwardera (da ne bi bila garbage collected)
forwarder_server = None

if __name__ == '__main__':
    # Kreiranje tabela ako ne postoje
    with app.app_context():
        try:
            db.create_all()
            logger.info(" Database tables checked/created.")
        except Exception as e:
            logger.error(f" Database connection failed: {e}")

    # Startovanje TCP Forwardera u pozadini
    # Sluša na portu 7000 za podatke sa hardvera
    try:
        logger.info("[TCP] Starting Forwarder TCP Server...")
        forwarder_server = ForwarderIngressServer(
            host="0.0.0.0", 
            port=7000, 
            flask_app=app, 
            socketio=socketio
        )
        forwarder_server.start()
    except Exception as e:
        logger.error(f" Failed to start TCP Server: {e}")

    # Startovanje Flask Servera
    logger.info("[APP] Starting ParkingOS V3.0 Backend on port 5000...")
    
    # --- GLAVNA PROMENA OVDE ---
    # debug=False sprečava pokretanje dva procesa
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)