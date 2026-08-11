# Zeltplatz Buchung

Buchungsverwaltung für Pfadfinder-Zeltlagerplätze als Home-Assistant-Add-on.

## Lokal starten (ohne Home Assistant)

Voraussetzungen: Python 3.12+ (lokal auch 3.14), Node.js 20+

```powershell
cd d:\Coding\Techuana_Homeassistant\zeltplatz-booking\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_dev.py
```

Zweites Terminal:

```powershell
cd d:\Coding\Techuana_Homeassistant\zeltplatz-booking\frontend
npm install
npm run dev
```

Oder vom Repo-Root (nach einmaligem Setup oben):

```powershell
npm run dev:api
npm run dev:ui
```

Cursor Preview / Browser: [http://localhost:5173](http://localhost:5173)

API-Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

SQLite-Datei: `zeltplatz-booking/.data/booking.db`

## Tests

```powershell
cd d:\Coding\Techuana_Homeassistant\zeltplatz-booking\backend
$env:DATA_DIR = "$((Get-Location).Path)\.testdata"
$env:DEV_MODE = "1"
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest -q
```

## Home Assistant Add-on

1. Dieses Repository als Add-on-Repository in HA hinzufügen (Supervisor → Add-on Store → Repositories).
2. Add-on **Zeltplatz Buchung** installieren und starten.
3. UI über die HA-Sidebar (Ingress) öffnen.

### Optionen

| Option | Bedeutung |
|--------|-----------|
| `timezone` | Zeitzone, Standard `Europe/Vienna` |
| `api_token` | Optional. Wenn gesetzt, müssen externe Clients Header `X-API-Token` senden. Ingress/localhost bleiben ohne Token erlaubt. |

Daten liegen persistent unter `/data/booking.db` (im HA-Backup enthalten).

## REST API

Basis: `/api/v1`

- `GET /health`
- `GET /countries`
- `GET/POST /pitches`
- `GET/PATCH/DELETE /pitches/{id}`
- `GET /pitches/available?start=&end=`
- `GET /pitches/{id}/bookings`
- `GET/POST /bookings` (Body optional `services: [{service_id, quantity}]`, Response `warnings[]`)
- `GET /bookings/gantt?from_date=&to_date=`
- `GET/PATCH/DELETE /bookings/{id}`
- `GET/POST /service-groups`, `PATCH/DELETE /service-groups/{id}`
- `GET/POST /services`, `PATCH/DELETE /services/{id}`
- `GET /services/availability?start=&end=`

Buchungsintervall ist halb-offen **`[start_date, end_date)`** — `end_date` ist der Abreisetag und zählt nicht als belegte Nacht.

Zusatzdienste prüfen den **Peak-Bestand über den Zeitraum**. Bei Überschreitung erscheint eine Bestätigung: **Buchung trotzdem speichern** oder **Zurück zur Planung** (ohne Speichern).

## Smoke-Check

1. Unter **Zeltplätze** einen Platz mit Saison anlegen.
2. **Neue Buchung**: Gruppe, Zeitraum, Personen, freie Plätze per Checkbox.
3. Gantt und Kalender zeigen die Buchung.
4. Überlappende Buchung auf demselben Platz → Fehler 409.
