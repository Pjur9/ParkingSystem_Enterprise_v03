import socket
import threading
import logging
import json
from datetime import datetime
from dataclasses import dataclass

# Importujemo modele i novi servis
from models import db, Device, Gate, CredentialType, ScanLog
from services.parking_service import ParkingLogicService

# Podesavanje logger-a
logger = logging.getLogger("forwarder")
logger.setLevel(logging.INFO)

# Hardverski portovi (Simulacija razlicitih ulaza na kontroleru)
DATA_STREAM_PORT = 7000
STATUS_STREAM_PORT = 7001

# Mapiranje lokalnog porta na tip kredenšl-a
# (Ovo zavisi od konfiguracije hardvera: koji čitač je na kom portu)
ROLE_BY_LOCAL_PORT = {
    5000: "QR",
    5050: "RFID",
    5555: "LPR",
}

@dataclass(frozen=True)
class ForwarderMessage:
    device_ip: str
    local_port: int
    payload: str
    received_at: datetime

class ForwarderIngressServer:
    """
    TCP Server koji slusa hardverske uredjaje.
    Radi u zasebnom thread-u i ne blokira Flask.
    """

    def __init__(self, host, port, flask_app, socketio):
        self.host = host
        self.port = port
        self.app = flask_app      # Treba nam za DB Context
        self.socketio = socketio  # Treba nam za Real-time evente
        
        # Inicijalizujemo Logic Engine
        # Napomena: Logic Service ce koristiti app context unutar svojih metoda
        self.parking_logic = ParkingLogicService(socketio)
        
        self._stop_event = threading.Event()

    def start(self):
        """Pokrece TCP listener u background thread-u"""
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()
        logger.info(f" Forwarder TCP Server listening on {self.host}:{self.port}")

    def _run_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind((self.host, self.port))
            sock.listen(5)
            
            while not self._stop_event.is_set():
                client_sock, addr = sock.accept()
                # Svaki klijent (uredjaj) dobija svoj thread za obradu
                client_handler = threading.Thread(
                    target=self.handle_client_connection,
                    args=(client_sock, addr)
                )
                client_handler.start()
                
        except Exception as e:
            logger.error(f"Critical Forwarder Error: {e}")
        finally:
            sock.close()

    def handle_client_connection(self, client_sock, addr):
        ip, port = addr
        # logger.debug(f"Device connected: {ip}")

        with client_sock:
            while True:
                try:
                    data = client_sock.recv(1024)
                    if not data:
                        break
                    
                    message_str = data.decode('utf-8').strip()
                    if not message_str:
                        continue
                    
                    # Parsiramo poruku (Ocekujemo format ili raw string)
                    # Pretpostavka: Hardver salje podatke na port na koji je zakacen
                    # Ali ovde slusamo na jednom portu, pa cemo simulirati 'local_port' logiku
                    # ili koristiti raw payload.
                    
                    # Za potrebe V3.0, pretpostavljamo da uredjaj salje:
                    # "TYPE:PAYLOAD" (npr "RFID:E20030..." ili "HEARTBEAT")
                    
                    self.process_message(ip, message_str)

                except ConnectionResetError:
                    break
                except Exception as e:
                    logger.error(f"Error handling client {ip}: {e}")
                    break

    def process_message(self, ip, raw_message):
        """
        Glavna logika obrade poruke.
        Mora da radi unutar Flask App Context-a jer pristupa bazi.
        """
        
        # 1. HEARTBEAT (Tehnicki Event)
        if "HEARTBEAT" in raw_message or "KeepAlive" in raw_message:
            self.socketio.emit('device_status', {
                'device_ip': ip,
                'status': 'ONLINE',
                'last_seen': datetime.now().isoformat()
            })
            return

        # 2. POSLOVNA LOGIKA (Mora u App Context)
        with self.app.app_context():
            # A. Identifikacija Gejta na osnovu IP-a
            device = Device.query.filter_by(ip_address=ip).first()
            
            if not device:
                logger.warning(f"Message from UNKNOWN device IP: {ip}")
                return

            gate_id = device.gate_id
            
            # B. Parsiranje Payloada
            # Primer formata: "RFID:E2801160600002046654C463"
            try:
                if ":" in raw_message:
                    scan_type_str, scan_value = raw_message.split(":", 1)
                else:
                    # Fallback ako hardver salje samo kod (pretpostavimo RFID)
                    scan_type_str = "RFID"
                    scan_value = raw_message

                scan_type_str = scan_type_str.upper().strip()
                scan_value = scan_value.strip()

                # Mapiranje stringa u Enum (Validacija unosa)
                if scan_type_str not in ["RFID", "LPR", "QR", "PIN"]:
                     # Ako hardver salje nesto cudno, ignorisi ili loguj kao gresku
                     logger.warning(f"Unknown scan type: {scan_type_str}")
                     return

            except ValueError:
                return

            # C. Pozivanje Logic Engine-a
            # Ovo vraca dict { "allow": bool, "reason": str ... }
            decision = self.parking_logic.handle_scan(gate_id, scan_type_str, scan_value)
            
            # D. Reakcija (Feedback loop ka hardveru)
            if decision.get("allow"):
                logger.info(f" OPENING GATE {gate_id} for {scan_value}")
                self.send_open_command(ip)
            else:
                logger.info(f" ACCESS DENIED at {gate_id}: {decision.get('reason')}")
                # Opciono: Posalji poruku na displej rampe
                # self.send_display_message(ip, "Access Denied")

    def send_open_command(self, ip, port=5005):
        """
        Šalje raw TCP signal kontroleru da otvori relej.
        Vraća (success: bool, message: str)
        """
        try:
            logger.info(f"Connecting to hardware controller at {ip}:{port}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0) # Timeout 2 sekunde
                s.connect((ip, port))
                s.sendall(b"CMD:OPEN\n")
                
                # Čekamo potvrdu od hardvera (opciono, ali dobro za debug)
                response = s.recv(1024).decode().strip()
                logger.info(f"Hardware confirmed: {response}")
                return True, response
                
        except ConnectionRefusedError:
            err_msg = f"Connection Refused at {ip}:{port}. Is the device online?"
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"Socket Error: {str(e)}"
            logger.error(err_msg)
            return False, err_msg

    def open_gate_manual(self, gate_id):
        """
        Metoda koju poziva API za ručno otvaranje.
        1. Nalazi uređaj.
        2. Zove send_open_command.
        3. Upisuje u LOG (da se vidi na dashboardu).
        """
        with self.app.app_context():
            # 1. Nadji glavni kontroler za ovaj gate
            device = Device.query.filter_by(gate_id=gate_id).first()
            gate = Gate.query.get(gate_id)
            
            if not device:
                return False, "No hardware controller found for this gate"

            # 2. Pošalji komandu (koristimo postojeću funkciju)
            success, message = self.send_open_command(device.ip_address, device.port)

            if success:
                # 3. Ako je uspelo, upiši u Audit Log
                # Ovo je ključno da bi se na Frontendu pojavio zeleni red
                new_log = ScanLog(
                    gate_id=gate.id,
                    gate_name_snapshot=gate.name,
                    scan_type=CredentialType.PIN, # PIN kao oznaka za manuelno/admin
                    raw_payload="MANUAL_OVERRIDE",
                    is_access_granted=True,
                    denial_reason="MANUAL_OPEN_DASHBOARD",
                    resolved_user_id=None 
                )
                db.session.add(new_log)
                db.session.commit()
                
                # Emituj event da se Dashboard odmah osvježi (bez refresha stranice)
                # Serijalizacija loga bi trebala biti u utils, ali ovdje cemo poslati osnovno
                self.socketio.emit('access_log', {
                    "id": new_log.id,
                    "gate_name": gate.name,
                    "scan_type": "PIN",
                    "payload": "MANUAL_OVERRIDE",
                    "allowed": True,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                
                return True, f"Gate opened via {device.ip_address}. HW: {message}"
            
            else:
                return False, message