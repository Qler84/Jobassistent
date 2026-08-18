# Job-Assistent (Web)

Webbasierte Neuentwicklung der Job-Assistent-Desktop-App: automatisierte Jobsuche (Bundesagentur für
Arbeit + Job-Alert-E-Mails), lokales Match-Scoring, Claude-generierte Anschreiben mit manueller
Freigabe, SMTP-Versand und IMAP-Status-Tracking. Mehrbenutzerfähig, responsive (Mobile First).

## Architektur

```
/backend   FastAPI (Python) - REST-API, Business-Logik, Postgres via SQLAlchemy
/frontend  React + Vite + Tailwind CSS - SPA, spricht nur mit der API
render.yaml  Render.com Blueprint fuer beide Services
```

- **Kein automatisches Scraping**: Stellenangebote kommen ausschließlich über die öffentliche
  BA-Jobsuche-API und über Job-Alert-E-Mails, die LinkedIn/Xing/StepStone/Indeed dem Nutzer ohnehin
  regulär zuschicken (vom Nutzer selbst eingerichtete gespeicherte Suche/Alert).
- **Anschreiben nie automatisch versendet**: Ein Anschreiben wird nur nach Klick auf „Bestätigen“
  bei einer Stellenanzeige generiert, und nur nach explizitem Klick auf „Freigeben & Senden“ **und**
  nur, wenn der automatische Versand in den Einstellungen aktiv aktiviert wurde (Vorschau-Modus ist
  Standard nach Registrierung).
- **Mehrbenutzerfähig**: jeder Nutzer hat ein eigenes Konto (E-Mail + Passwort), eigenes Profil,
  eigene Jobs/Bewerbungen und eigene, verschlüsselt gespeicherte Zugangsdaten (SMTP/IMAP/Claude
  API-Key).

## Sicherheitsmodell: Unterschied zur Desktop-App

Die Desktop-App verschlüsselte Zugangsdaten mit einem Schlüssel, der ausschließlich aus dem
Master-Passwort des Nutzers im RAM abgeleitet wurde („Zero-Knowledge“ – selbst der Entwickler hätte
die Daten nicht entschlüsseln können). Ein zustandsloser Web-Server kann dieses Modell nicht
sinnvoll abbilden: jeder Request (z.B. „E-Mail jetzt prüfen“) braucht Zugriff auf die Zugangsdaten,
ohne dass der Nutzer sein Passwort bei jeder Aktion erneut eingibt.

Stattdessen: normales Login per Passwort-Hash (bcrypt), und die Zugangsdaten (SMTP/IMAP-Passwort,
Anthropic API-Key) werden serverseitig mit einem aus `APP_SECRET_KEY` abgeleiteten Schlüssel
verschlüsselt in der Datenbank abgelegt („at rest“). Das schützt bei einem reinen Datenbank-Diebstahl,
nicht aber vor dem Betreiber des Servers selbst. Für eine rein persönliche Nutzung (ein Nutzer
betreibt seine eigene Instanz) ist das ein sinnvoller, praxistauglicher Kompromiss.

## Lokale Entwicklung

### Voraussetzungen

- Python 3.12+, Node.js 20+
- Eine Postgres-Datenbank (siehe unten) oder lokal `sqlite:///dev.db` für schnelles Ausprobieren

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows; unter Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # DATABASE_URL und APP_SECRET_KEY eintragen
uvicorn app.main:app --reload
```

Die API läuft auf `http://localhost:8000`, interaktive Doku unter `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev
```

Die App läuft auf `http://localhost:5173`.

## Kostenlose Postgres-Datenbank einrichten (Neon oder Supabase)

Render's eigene kostenlose Postgres-Instanz wird nach 30 Tagen automatisch gelöscht – für eine App,
die Bewerbungsverläufe dauerhaft speichern soll, ungeeignet. Stattdessen eine externe, dauerhaft
kostenlose Datenbank:

**Neon.tech** (empfohlen, einfachster Weg):
1. Kostenloses Konto auf [neon.tech](https://neon.tech) anlegen.
2. Neues Projekt erstellen.
3. Den angezeigten Connection-String kopieren (Format `postgresql://user:pass@host/dbname?sslmode=require`).

**Supabase** (Alternative):
1. Kostenloses Konto auf [supabase.com](https://supabase.com) anlegen.
2. Neues Projekt erstellen, unter „Connect“ den Connection-String (URI, „Transaction“-Modus) kopieren.

Der Connection-String wird als `DATABASE_URL` sowohl lokal (`.env`) als auch auf Render (Dashboard →
Environment) eingetragen.

## Deployment auf Render.com

1. Repository zu GitHub pushen (Render deployt aus einem Git-Repository).
2. Im Render-Dashboard: „New +“ → „Blueprint“ → Repository auswählen. Render liest `render.yaml` und
   legt automatisch zwei Services an: `job-assistent-backend` (Web Service) und
   `job-assistent-frontend` (Static Site).
3. `APP_SECRET_KEY` wird automatisch generiert (`generateValue: true`). Folgende Variablen müssen
   nach dem ersten Deploy manuell im Dashboard gesetzt werden (bewusst nicht im Blueprint, da sie von
   den erzeugten Service-URLs abhängen bzw. Secrets sind):
   - **Backend** (`job-assistent-backend` → Environment):
     - `DATABASE_URL` = Connection-String von Neon/Supabase (siehe oben)
     - `CORS_ORIGINS` = die URL des Frontend-Services, z.B. `https://job-assistent-frontend.onrender.com`
   - **Frontend** (`job-assistent-frontend` → Environment):
     - `VITE_API_URL` = die URL des Backend-Services, z.B. `https://job-assistent-backend.onrender.com`
     - Wichtig: Vite bündelt Umgebungsvariablen beim Build – nach dem Setzen von `VITE_API_URL` muss
       das Frontend einmal manuell neu deployt werden („Manual Deploy“ im Dashboard).
4. Beide Services prüfen (Backend: `<backend-url>/health` sollte `{"status":"ok"}` liefern; Frontend:
   Login-Seite sollte laden).
5. Ein Konto über „Registrieren“ anlegen und in den Einstellungen die eigenen Zugangsdaten
   (SMTP/IMAP/Claude API-Key) hinterlegen.

### Bekannte Einschränkungen des kostenlosen Tiers

- Der Backend-Web-Service schläft nach 15 Minuten Inaktivität ein und braucht beim nächsten Aufruf
  ca. 30-50 Sekunden zum Aufwachen – kein Bug, normales Verhalten des Render-Free-Tiers.
- Es läuft kein dauerhafter Hintergrund-Job für automatisches Postfach-Prüfen (das würde einen
  bezahlten Render Cron Job erfordern). Stattdessen: manueller „Postfach jetzt prüfen“-Button im
  Dashboard und im Bewerbungen-Bereich.
- Hochgeladene Anlagen (Lebenslauf, Zeugnisse) liegen als Binärdaten direkt in der Postgres-Datenbank,
  nicht auf der Festplatte des Web-Service (die ist beim kostenlosen Tier flüchtig und geht bei jedem
  Neustart/Redeploy verloren).

## Umgebungsvariablen-Referenz

### Backend (`backend/.env` bzw. Render-Dashboard)

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `DATABASE_URL` | ja | Postgres-Connection-String (Neon/Supabase/eigene Instanz) |
| `APP_SECRET_KEY` | ja | Langer Zufallsstring; Basis für JWT-Signierung und Verschlüsselung der Zugangsdaten |
| `CORS_ORIGINS` | ja | Kommagetrennte Liste erlaubter Frontend-Origins |

### Frontend (`frontend/.env`)

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `VITE_API_URL` | ja | Basis-URL des Backends |

## Tests

Kein automatisierter Test-Suite-Aufbau in diesem MVP – Verifikation erfolgte durch manuelles
End-to-End-Durchklicken (Registrierung, Login, Profil speichern, Job bestätigen, Anschreiben-Entwurf
speichern, Versand-Sperre bei deaktiviertem Auto-Versand) gegen eine lokale SQLite-Instanz.
