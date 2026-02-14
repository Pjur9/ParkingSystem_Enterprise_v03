📘 ParkingOS Enterprise v3.0 - System Design Document (SDD)

Verzija: 3.0.1
Datum: Februar 2026.
Autor: Architecture Team
Status: Alpha / Development

1. 🌍 Uvod i Vizija Projekta

ParkingOS v3.0 je SaaS (Software-as-a-Service) platforma za upravljanje kontrolom pristupa, naplatom i kapacitetima parking sistema. Sistem je dizajniran da reši problem fragmentacije hardvera u industriji parkinga.

Ključni Diferencijatori

Hardware Agnostic: Sistem ne zanima ko je proizvođač kamere ili rampe. Komunicira putem generičkih TCP stream-ova.

Configuration Driven: Poslovna logika (npr. "Zabrani ulaz ako je zona puna") nije hardkodovana, već se definiše kroz bazu podataka kao "Pravilo" (Validation Rule).

Dynamic Hierarchy: Podržava neograničeno gnježđenje zona (Aerodrom -> Garaža A -> Nivo 2 -> VIP Sekcija).

2. 🏗️ Arhitektura Sistema

Sistem koristi troslojnu arhitekturu (Three-Tier Architecture) sa asinhronom komunikacijom ka hardveru.

A. Hardware Layer (The Edge)

Uloga: Prikupljanje sirovih podataka sa terena.

Protokol: TCP/IP (Raw Stream).

Format Poruke: Hardver šalje podatke na definisani port (npr. 7000).

Format: DEVICE_IP:PORT + PAYLOAD

Primer: 192.168.1.55:5050 RFID:12345

B. Backend Layer (The Brain) - Python/Flask

Core: Flask aplikacija koja servira REST API i Socket.IO.

Forwarder Service (services/forwarder_tcp.py):

Sluša TCP saobraćaj na portovima 7000-7005.

Normalizuje podatke (uklanja šum).

Identifikuje Gate na osnovu IP adrese uređaja (tabela Devices).

Logic Service (services/parking_service.py):

Mozak sistema. Prima zahtev za ulaz, povlači pravila iz baze i vraća ALLOW ili DENY.

Database: PostgreSQL (Relaciona baza).

C. Frontend Layer (The Face) - Next.js

Tehnologije: Next.js 14+ (App Router), TypeScript, Tailwind CSS.

Komunikacija:

REST API: Za CRUD operacije (Korisnici, Podešavanja).

Socket.IO: Za live feed (Logovi prolazaka, Status rampi).

3. 💾 Model Podataka (Database Schema)

Baza je normalizovana i optimizovana za brzinu i fleksibilnost.

3.1 Identity & Access Management (IAM)

User: Entitet (Čovek ili Firma). Ima role_id i tenant_id.

Credential: Ključ za pristup. Veza 1:N sa User-om.

Tipovi: RFID, LPR (Tablica), QR, PIN.

Primer: Marko ima i Karticu (RFID) i Tablicu (LPR).

Role: Definiše prava pristupa i imunitete (npr. can_ignore_capacity).

Tenant: Firma koja zakupljuje parking mesta (B2B logika).

3.2 Infrastructure & Hardware

Zone: Hijerarhijski prostor. Svaka zona ima capacity i occupancy.

Self-Referencing: Zona može imati parent_zone_id.

Gate: Logička tačka prolaza. Povezuje dve zone (zone_from -> zone_to).

Device: Fizički hardver. Mapira IP_ADDRESS -> GATE_ID.

Ovo omogućava da jedna rampa ima više uređaja (Kameru, Čitač, Ekran).

3.3 Logic Engine (The "Secret Sauce")

ValidationRule: Umesto if naredbi u kodu, pravila su redovi u bazi.

rule_type: Šta proveravamo? (CHECK_CAPACITY, CHECK_ANTIPASSBACK...)

scope: Gde važi? (GLOBAL, ZONE, GATE, ROLE).

is_enabled: Prekidač ON/OFF.

ParkingSession: Prati boravak vozila. Kreira se na ulazu, zatvara na izlazu.

ScanLog: Audit log. Čuva sve, čak i odbijene pokušaje.

4. ⚙️ Tok Podataka (Data Flow) - Life of a Scan

Šta se dešava kada vozilo dođe na rampu?

Hardware Event: Kamera (IP: 10.0.0.50) šalje string BG-123-AA na port 7000.

Forwarder Processing:

Forwarder prima paket.

Pita bazu: "Kome pripada IP 10.0.0.50?" -> Odgovor: "Gate ID 1 (Glavni Ulaz)".

Šalje zahtev ParkingLogicService-u: "Korisnik sa tablicom BG-123-AA želi da prođe kroz Gate 1."

Identification:

Servis traži Credential sa vrednošću BG-123-AA.

Nalazi korisnika "Marko Marković" (Role: VIP).

Rules Validation:

Sistem povlači sva aktivna pravila za Gate 1, Zonu Garaža, i Rolu VIP.

Provera 1: Da li je Garaža puna? -> DA.

Provera 2: Da li VIP ima imunitet na popunjenost? -> DA (podešeno u Role).

Rezultat: ALLOW.

Execution (Side Effects):

Otvara se transakcija u bazi.

Kreira se ParkingSession.

Povećava se occupancy za zonu Garaža.

Šalje se signal "OPEN" nazad na kontroler rampe.

Emituje se WebSocket event ka Frontendu.

5. 🛠️ Uputstvo za Developere (Setup Guide)

Preduslovi

Python 3.10+

Node.js 18+

PostgreSQL (lokalno ili Docker)

1. Backend Setup

cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Kreiranje .env fajla (podesiti DATABASE_URL)
# Inicijalizacija baze sa test podacima
python seed_heavy.py

# Pokretanje servera (API + TCP Listener)
python app.py


2. Frontend Setup

cd frontend
npm install
npm run dev
# Otvori http://localhost:3000


3. Testiranje bez Hardvera

Koristi ugrađene skripte za simulaciju saobraćaja:

# Simulira 100 vozila koja ulaze/izlaze velikom brzinom
python backend/stress_test.py


6. 🚀 Roadmap i Sledeći Koraci (Next Gen)

Ovo su smernice za sledećeg developera ili AI asistenta:

Billing Engine (Prioritet 1):

Implementirati logiku u ParkingService pod CHECK_PAYMENT.

Dodati tabele PriceList i Transaction.

Logika: Cena = (Vreme_Izlaska - Vreme_Ulaska) * Tarifa.

Authentication & Security:

Zaštititi /api/settings i /api/users rute.

Implementirati JWT (JSON Web Token) login za Administratore.

Reporting Modul:

Kreirati API endpoint koji vraća statistiku (Zarada po danu, Zauzeće po satu).

Dodati grafove na Dashboard (koristeći recharts ili chart.js).

Hardware Heartbeat:

Implementirati "ping" mehanizam da Backend zna ako je kamera offline pre nego što neko pokuša da uđe.

Dokument generisan na osnovu analize koda ParkingOS v3.0 repozitorijuma.