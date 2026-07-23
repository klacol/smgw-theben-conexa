# CONEXA 3.0 Client-Bibliothek

Eine vollständige Python-Client-Bibliothek für das **Theben CONEXA 3.0 Smart Meter Gateway**, die alle dokumentierten API-Endpunkte der IF_GW_CON Schnittstelle unterstützt.

## 🎯 Features

- ✅ **Vollständige API-Abdeckung**: Alle dokumentierten Endpunkte implementiert
- ✅ **TLS 1.2 Support**: Sichere Kommunikation mit Client-Zertifikaten
- ✅ **HTTP Digest Authentication**: Authentifizierung mit Benutzername/Passwort
- ✅ **TOFU (Trust On First Use)**: Automatisches Zertifikatsmanagement
- ✅ **Type Hints**: Vollständige Typisierung für bessere IDE-Unterstützung
- ✅ **Dataclasses**: Strukturierte Datenmodelle
- ✅ **Error Handling**: Umfassende Fehlerbehandlung
- ✅ **Logging**: Integrierte Logging-Unterstützung
- ✅ **Context Manager**: Automatische Ressourcenverwaltung

## 📋 Voraussetzungen

- Python 3.8 oder höher
- Zugriff auf ein CONEXA 3.0 Smart Meter Gateway
- Netzwerkverbindung zum Gateway

## 🚀 Installation

1. **Repository klonen:**
```bash
git clone <repository-url>
cd smgw-theben-conexa
```

2. **Virtuelle Umgebung erstellen:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate  # Windows
```

3. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

4. **Umgebungsvariablen konfigurieren:**
Erstellen Sie eine `.env`-Datei im Hauptverzeichnis:
```env
CONEXA_IP_ADDRESS=192.168.1.100
CONEXA_PORT=443
CONEXA_USERNAME=ihr_benutzername
CONEXA_PASSWORD=ihr_passwort
```

## 📚 Schnellstart

### Einfaches Beispiel

```python
from conexa_client import ConexaClient

# Client erstellen
client = ConexaClient(
    ip_address="192.168.1.100",
    port=443,
    username="user",
    password="password"
)

# Verbinden
client.connect()
print("✓ Verbindung hergestellt")

# Gateway-Informationen abrufen
info = client.get_gateway_info()
print(f"Gateway: {info.smgw_id}")
print(f"Firmware: {info.firmware_info.version}")

# Verbindung schließen
client.close()
```

### Mit Context Manager

```python
from conexa_client import create_client_from_env

# .env-Datei wird automatisch geladen
with create_client_from_env() as client:
    client.connect()
    
    # Gateway-Informationen
    info = client.get_gateway_info()
    print(f"Gateway: {info.smgw_id}")
    
    # Vertragsdaten
    usage_points = client.get_user_info()
    for up in usage_points:
        print(f"TAF: {up.usage_point_name}")
    
# Session wird automatisch geschlossen
```

## 🔧 API-Dokumentation

### Authentifizierung

```python
# Verbindung herstellen
client.connect()
```

### Gateway-Informationen

```python
# Gateway-Informationen abrufen
info = client.get_gateway_info()

print(f"Gateway-ID: {info.smgw_id}")
print(f"Status: {info.smgw_state}")
print(f"Zeit: {info.smgw_time}")
print(f"Firmware: {info.firmware_info.version}")
```

### Vertragsdaten

```python
# Alle Tarifanwendungsfälle abrufen
usage_points = client.get_user_info()

for up in usage_points:
    print(f"Name: {up.usage_point_name}")
    print(f"TAF-Nummer: {up.taf_number}")
    print(f"Status: {up.taf_state}")
    print(f"Zähler: {[m.meter_id for m in up.meter]}")
```

### Vertrags-Details

```python
from conexa_client import DatabaseType

# Details für einen Tarifanwendungsfall
details = client.get_usage_point_info(
    usage_point_id="01005e318021.taf1-1.sm",
    database=DatabaseType.ORIGIN
)

print(f"TAF-Profil: {details.taf_profile}")
print(f"Transparenz-Bit: {details.transparency_bit}")

# Messkanäle anzeigen
for db in details.databases:
    if "channels" in db:
        for channel in db["channels"]:
            print(f"OBIS: {channel['obis']}")
```

### Logdaten

```python
# Letzte 100 Logeinträge
log_entries = client.get_log(count=100)

for entry in log_entries:
    print(f"[{entry.time}] {entry.message}")

# Logeinträge für Zeitraum
log_entries = client.get_log(
    fromtime="2024-01-01T00:00:00Z",
    totime="2024-01-31T23:59:59Z"
)

# Ab bestimmtem Index
log_entries = client.get_log(fromindex=1000, count=50)
```

### Messwerte

```python
from conexa_client import DatabaseType

# Letzten Messwert abrufen
readings = client.get_readings(
    usage_point_id="01005e318021.taf1-1.sm",
    database=DatabaseType.ORIGIN,
    last_reading=True
)

for channel_reading in readings:
    print(f"Kanal: {channel_reading.obis}")
    for reading in channel_reading.readings:
        print(f"Wert: {reading.value}")
        print(f"Zeit: {reading.capture_time}")

# Messwerte für Zeitraum
readings = client.get_readings(
    usage_point_id="01005e318021.taf1-1.sm",
    database=DatabaseType.ORIGIN,
    fromtime="2024-01-01T00:00:00Z",
    totime="2024-01-07T23:59:59Z"
)

# Nur bestimmte Kanäle
readings = client.get_readings(
    usage_point_id="01005e318021.taf1-1.sm",
    database=DatabaseType.ORIGIN,
    channels=["0100010800ff", "0100020800ff"],  # Bezug und Einspeisung
    last_reading=True
)
```

### Selbsttest

```python
# Selbsttest auslösen
try:
    success = client.trigger_self_test()
    if success:
        print("Selbsttest ausgelöst - prüfen Sie das Logbuch")
except ConexaAPIError as e:
    if e.status_code == 403:
        print("Selbsttest kann nur alle 10 Minuten ausgeführt werden")
```

## 🗂️ Datenbank-Typen

Die Bibliothek unterstützt alle dokumentierten Messwertlisten:

```python
from conexa_client import DatabaseType

DatabaseType.ORIGIN      # Originäre Messwertliste
DatabaseType.DERIVED     # Abgeleitete Messwertliste
DatabaseType.CALCULATED  # Tarifumschaltmesswertliste (nur TAF2)
DatabaseType.DAILY       # Tageswerte
```

## ⚠️ Fehlerbehandlung

Die Bibliothek definiert spezifische Exceptions:

```python
from conexa_client import (
    ConexaClientError,          # Basis-Exception
    ConexaAuthenticationError,  # Authentifizierungsfehler
    ConexaNetworkError,         # Netzwerkfehler
    ConexaAPIError              # API-Fehler
)

try:
    client.connect()
    info = client.get_gateway_info()
    
except ConexaAuthenticationError as e:
    print(f"Authentifizierung fehlgeschlagen: {e}")
    
except ConexaNetworkError as e:
    print(f"Netzwerkproblem: {e}")
    
except ConexaAPIError as e:
    print(f"API-Fehler: {e} (Status: {e.status_code})")
    
except ConexaClientError as e:
    print(f"Allgemeiner Fehler: {e}")
```

## 📊 OBIS-Codes

Häufig verwendete OBIS-Codes:

| OBIS-Code | Beschreibung |
|-----------|--------------|
| `0100010800ff` | Bezug Wirkenergie gesamt |
| `0100020800ff` | Einspeisung Wirkenergie gesamt |
| `0100010700ff` | Bezug Wirkleistung aktuell |
| `0100020700ff` | Einspeisung Wirkleistung aktuell |
| `01001f0700ff` | Strom L1 |
| `0100330700ff` | Strom L2 |
| `0100470700ff` | Strom L3 |
| `0100200700ff` | Spannung L1 |
| `0100340700ff` | Spannung L2 |
| `0100480700ff` | Spannung L3 |

## 🔍 Beispiele

Siehe [examples.py](examples.py) für vollständige Beispiele:

```bash
# Alle Beispiele anzeigen
python examples.py

# Interaktive Auswahl
python examples.py
```

Verfügbare Beispiele:
1. Grundlegende Verwendung
2. Vertragsdaten und Details
3. Messwerte abrufen
4. Logbuch-Analyse
5. Selbsttest auslösen
6. Fehlerbehandlung
7. Alle Messkanäle anzeigen

## 🔒 Sicherheit

### TLS-Zertifikate

Die Bibliothek implementiert **TOFU (Trust On First Use)**:

1. Beim ersten Verbindungsaufbau wird das Server-Zertifikat heruntergeladen
2. Das Zertifikat wird als `<ip_address>_public_cert.pem` gespeichert
3. Bei nachfolgenden Verbindungen wird dieses Zertifikat verwendet

```python
# Zertifikat manuell herunterladen
client.download_certificate(force=True)

# Eigenes Zertifikat verwenden
client = ConexaClient(
    ip_address="192.168.1.100",
    cert_file="mein_zertifikat.pem"
)
```

### SSL-Verifizierung

```python
# SSL-Verifizierung deaktivieren (nur für Tests!)
client = ConexaClient(
    ip_address="192.168.1.100",
    verify_ssl=False
)
```

## 🐛 Debugging

Logging aktivieren:

```python
import logging

# Debug-Level für detaillierte Ausgaben
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Nur conexa_client debuggen
logging.getLogger("conexa_client").setLevel(logging.DEBUG)
```

## 📝 Zeitformate

Die API verwendet ISO 8601 Zeitformate:

```python
# Format: YYYY-MM-DDTHH:MM:SSZ
"2024-01-15T14:30:00Z"

# Mit Zeitzone
"2024-01-15T14:30:00+01:00"

# Python datetime konvertieren
from datetime import datetime

now = datetime.now()
iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
```

## 🤝 Beitragen

Beiträge sind willkommen! Bitte:

1. Fork das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/amazing-feature`)
3. Committe deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Pushe den Branch (`git push origin feature/amazing-feature`)
5. Öffne einen Pull Request

## 📄 Lizenz

Dieses Projekt ist lizenziert unter der MIT-Lizenz - siehe [LICENSE](LICENSE) für Details.

## 🙏 Danksagungen

- Basierend auf der offiziellen Schnittstellenbeschreibung IF_GW_CON Version 1.4
- Theben AG für das CONEXA 3.0 Smart Meter Gateway

## 📞 Support

Bei Fragen oder Problemen:

- Öffnen Sie ein [Issue](../../issues)
- Konsultieren Sie die [offizielle Dokumentation](Docs/Schnittstellenbeschreibung%20IF_GW_CON.pdf)

## 🔄 Changelog

### Version 1.0.0 (2024)
- Initial release
- Vollständige API-Implementierung
- TOFU-Support
- Umfassende Fehlerbehandlung
- Beispiele und Dokumentation

---

**Hinweis:** Diese Bibliothek ist ein inoffizielles Client-Projekt und nicht mit Theben AG verbunden oder von ihr unterstützt.
