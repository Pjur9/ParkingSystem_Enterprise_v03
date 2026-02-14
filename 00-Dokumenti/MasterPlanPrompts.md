***

# 📂 DEO 1: MASTER CONTEXT (Ovo čuvaš kao "System Prompt")

Kada god počinješ novu sesiju sa AI-jem, ili želiš da ga "resetuješ" na pravi put, pošalji mu ovaj blok teksta. Ovo je "Biblija" projekta.

***

**ROLE:** You are a Senior Backend & Frontend Developer working under a Software Architect. You are building "ParkingOS v3.0".

**PROJECT OVERVIEW:**
"ParkingOS v3.0" is a SaaS/White-label Enterprise Smart Parking System. It manages parking access control, billing, and capacity for various clients (Airports, Hospitals, Malls, Private Lots).

**CORE ARCHITECTURE:**
*   **Backend:** Python (Flask), SQLAlchemy (PostgreSQL), Socket.IO (Async threading).
*   **Frontend:** Next.js (TypeScript, App Router), Tailwind CSS.
*   **Protocol:** Custom TCP Forwarder receiving raw data `IP:PORT PAYLOAD` from hardware.
*   **Hardware Agnostic:** Supports RFID, LPR (License Plate), QR Codes via generic TCP streams.

**KEY BUSINESS RULES (V3.0):**
1.  **Dynamic Hierarchy:** Zones can be nested infinitely (Root -> Garage -> Level 1 -> VIP).
2.  **Toggle-based Validation:** Every rule (Capacity, APB, Schedule, Payment) can be toggled ON/OFF at Global, Zone, Gate, or User levels.
3.  **Role-Based Access (RBAC):** Users have flexible Roles (e.g., "VIP", "Staff", "Guest"). Permissions are granular (e.g., `can_ignore_capacity`, `is_billable`).
4.  **Mixed-Use:** Supports Tenants (Companies with quotas) and Public Users (Pay-per-hour) simultaneously.

**CURRENT STATUS:**
*   Basic Python backend exists (Flask + TCP Forwarder).
*   Basic Next.js frontend initialized.
*   **GOAL:** Refactor database to V3.0 standards (Roles, Configs) and build the advanced Dashboard.

***

***

# 📂 DEO 2: EXECUTION ROADMAP (Korak po Korak Instrukcije)

Ovo su promptovi koje ćeš mi slati, jedan po jedan. Svaki prompt je jedan "Ticket" koji programer treba da reši.

## 🟢 FAZA 1: Refactoring Baze (Temelj V3.0)

### 📋 Korak 1.1: Database Schema Overhaul
*Cilj: Ažuriranje `models.py` da podrži Role i Toggle konfiguraciju.*

> **Prompt za AI:**
> "Koristeći Master Context, moramo ažurirati `models.py` na V3.0 standard. Trenutna baza je previše jednostavna.
>
> 1.  **Kreiraj `Role` model:** Ime, opis, i boolean polja za permisije (`can_ignore_capacity`, `can_ignore_antipassback`, `is_vip`, `limit_zones`).
> 2.  **Ažuriraj `User/Card`:** Korisnici više nemaju direktno flagove, već `role_id`. Dodaj podršku za `Tenant` (može biti NULL).
> 3.  **Kreiraj `ValidationRule` model:** Ovo menja stari `ValidationConfig`. Treba da ima polja: `scope` (GLOBAL, ZONE, GATE), `target_id` (ID zone/rampe), `rule_type` (npr. 'CHECK_CAPACITY', 'CHECK_SCHEDULE'), i `is_enabled` (Boolean).
> 4.  **Ažuriraj `Zone`:** Dodaj `parent_zone_id` za hijerarhiju.
>
> Napiši kompletan, ispravan `models.py` kod koristeći SQLAlchemy."

### 📋 Korak 1.2: Business Logic Update
*Cilj: Ažuriranje `parking_service.py` da koristi nove tabele.*

> **Prompt za AI:**
> "Baza je ažurirana. Sada moramo prepraviti `parking_service.py` da koristi novu logiku.
>
> 1.  Promeni `handle_scan` funkciju. Umesto hardkodovanih provera, sistem mora da učita aktivna pravila iz `ValidationRule` tabele.
> 2.  Implementiraj 'Chain of Responsibility':
>     - Prvo proveri Global pravila.
>     - Zatim pravila Zone u kojoj je rampa.
>     - Zatim pravila Rampe.
> 3.  Implementiraj proveru Rola: Ako korisnik ima rolu sa `can_ignore_capacity=True`, preskoči proveru kapaciteta čak i ako je pravilo uključeno.
>
> Napiši ažurirani `parking_service.py`."

### 📋 Korak 1.3: Seeding V3.0 Data
*Cilj: Napuniti bazu bogatim podacima za testiranje.*

> **Prompt za AI:**
> "Treba mi novi `seed.py` koji demonstrira moć V3.0 sistema.
>
> 1.  Kreiraj 2 Zone: 'Aerodrom' (Parent) i 'VIP Garaža' (Child).
> 2.  Kreiraj 3 Role: 'Direktor' (Ignore all), 'Zaposleni' (Standard), 'Gost' (Strict rules).
> 3.  Kreiraj Tenanta 'AirSerbia' sa kvotom 50.
> 4.  Kreiraj pravilo: Isključi 'CHECK_PAYMENT' globalno (Demo dan).
> 5.  Kreiraj par korisnika za svaku rolu.
>
> Daj mi kod za `seed.py`."

***

## 🟡 FAZA 2: Backend API & Real-time (Veze)

### 📋 Korak 2.1: API Endpoints Refactor
*Cilj: API mora da vraća podatke u formatu koji Frontend razume.*

> **Prompt za AI:**
> "Ažuriraj `api/routes_gates.py` i `api/routes_cards.py`.
>
> 1.  `/api/gates`: Pored statusa rampe, vrati i informaciju kojoj Zoni pripada i koja su pravila trenutno aktivna na njoj.
> 2.  `/api/dashboard/stats`: Novi endpoint koji vraća trenutno zauzeće po zonama (uključujući hijerarhiju) i broj online uređaja.
> 3.  Osiguraj da su svi odgovori JSON serijalizabilni (pazi na datetime objekte)."

### 📋 Korak 2.2: Socket.IO Events
*Cilj: Standardizacija događaja koje šaljemo Frontendu.*

> **Prompt za AI:**
> "Treba da definišemo Socket.IO događaje u `forwarder_tcp.py` i `parking_service.py`.
>
> 1.  Kada se rampa otvori/odbije: Emituj `access_log` sa detaljima (Ko, Gde, Zašto, Slika_URL ako postoji).
> 2.  Kada stigne heartbeat: Emituj `device_status`.
> 3.  Kada se promeni zauzeće zone: Emituj `occupancy_update`.
>
> Napiši mi isečke koda gde se ovi eventi emituju."

***

## 🔵 FAZA 3: Frontend Dashboard (Next.js)

### 📋 Korak 3.1: Layout & Navigation
*Cilj: Osnovni izgled aplikacije.*

> **Prompt za AI:**
> "Prelazimo na Frontend. Koristimo Next.js 14+ i Tailwind.
>
> 1.  Kreiraj `components/Sidebar.tsx` sa linkovima: Dashboard, Live Feed, Users, Settings.
> 2.  Kreiraj `app/layout.tsx` koji uključuje Sidebar i drži glavnu strukturu.
> 3.  Dizajn treba da bude moderan, 'Dark Mode' ready, enterprise izgled (sivo/plave nijanse)."

### 📋 Korak 3.2: Live Dashboard Component
*Cilj: Glavni ekran gde operater gleda šta se dešava.*

> **Prompt za AI:**
> "Kreiraj `app/page.tsx` (Dashboard).
>
> 1.  Podeli ekran na 3 dela:
>     - **Levo:** Lista Rampi (Card view) sa statusom (Online/Offline) i dugmetom 'Otvori'.
>     - **Sredina:** Statistika Zona (Progress barovi za zauzeće).
>     - **Desno:** Live Feed Logova (skrolujuća lista poslednjih ulazaka).
> 2.  Poveži se na Socket.IO server da se ovi podaci ažuriraju uživo bez refresha."

### 📋 Korak 3.3: User Management Table
*Cilj: CRUD operacije za korisnike.*

> **Prompt za AI:**
> "Kreiraj stranicu `app/users/page.tsx`.
>
> 1.  Tabela svih korisnika sa paginacijom.
> 2.  Kolone: Ime, Rola, Tenant, Tablica, Status (Aktivan/Blokiran).
> 3.  Dodaj dugme 'Add User' koje otvara Modal formu.
> 4.  Forma treba da povuče listu dostupnih Rola i Tenanta iz API-ja."

### 📋 Korak 3.4: Settings & Rules Configurator
*Cilj: Najvažniji deo - upravljanje pravilima.*

> **Prompt za AI:**
> "Kreiraj stranicu `app/settings/page.tsx`.
>
> 1.  Ovo je kontrolna tabla za `ValidationRules`.
> 2.  Prikaži matricu prekidača (Toggles).
>     - Redovi: Pravila (Capacity, APB, Schedule...).
>     - Kolone: Scope (Global, Zone A, Zone B...).
> 3.  Kada admin klikne na prekidač, šalje se API zahtev da se to pravilo upali/ugasi. Ovo mora biti veoma intuitivno."

***

## 🟣 FAZA 4: Deployment & Polish

### 📋 Korak 4.1: Dockerizacija
*Cilj: Da se ovo lako instalira kod klijenta.*

> **Prompt za AI:**
> "Napravi `Dockerfile` i `docker-compose.yml`.
>
> 1.  Servis 1: Postgres Baza.
> 2.  Servis 2: Backend (Python).
> 3.  Servis 3: Frontend (Next.js build).
> 4.  Podesi network da Frontend i Backend vide bazu."

***