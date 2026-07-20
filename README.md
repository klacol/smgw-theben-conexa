# API-Client für das Theben Conexa Smart Meter Gateway (SMGW)

Dieses Repo enthält Code und Dokumentation zur Anfrage des HAN-API des Smart Meter Gateway (SMGW) der Firma Theben. Der Code basiert auf Python.

## Verfügbare Implementierungen

### ✅ **Empfohlen: theben-conexa-requests.py** 
Die vollständig funktionsfähige Implementierung mit der Python Bibliothek `requests`.

**Features:**
- ✓ TOFU (Trust On First Use) mit automatischem Zertifikats-Download
- ✓ PING-Check vor dem Request
- ✓ SSL-Verifizierung mit SAN-Name-Extraktion
- ✓ Automatische HTTPS/HTTP-Erkennung basierend auf Port
- ✓ Digest-Authentifizierung (vollständig kompatibel)
- ✓ Detaillierte Fehlerbehandlung mit Timeouts

### ⚠️ **Experimentell: theben-conexa-httpx.py**
Asynchrone Implementierung mit der Python Bibliothek `httpx`.

**Status:**
- ✓ TOFU (Trust On First Use) implementiert
- ✓ PING-Check implementiert  
- ✓ SSL-Verifizierung implementiert
- ✗ **Digest-Auth-Kompatibilitätsproblem:** Der Theben Conexa SMGW schließt die Verbindung während der Digest-Authentifizierung (`RemoteProtocolError`)

**Hinweis:** Verwenden Sie die requests-Version für produktive Einsätze.

## Verwendung

Die API-Dokumentation findet man in der [Schnittstellenbeschreibung IF_GW_CON.pdf](https://github.com/klacol/smgw-theben-conexa/blob/main/Schnittstellenbeschreibung%20IF_GW_CON.pdf).

### Konfiguration

Zum Laden der Zugangsdaten bitte die Datei `.env` anlegen und wie folgt befüllen:

```shell
CONEXA_IP_ADDRESS=10.11.120.2  # oder der SAN-Name aus dem Zertifikat
CONEXA_PORT=443  # (oder einen anderen Port, z.B. wenn ein Proxy dazwischen ist)
CONEXA_USERNAME=30320426231LGZ0067558611
CONEXA_PASSWORD=IhrPasswort
```

### DNS-Konfiguration für SSL-Verifizierung

Für die vollständige SSL-Verifizierung muss der SAN-Name aus dem Zertifikat über DNS auflösbar sein:

**Windows Hosts-Datei** (`C:\Windows\System32\drivers\etc\hosts`):
```
10.11.120.2  ethe0300186023.sm
```

**Oder DNS-Server-Eintrag:**
```
ethe0300186023.sm.    IN    A    10.11.120.2
```

### Ausführung

Mit Python ausführen:

```bash
# Empfohlene Version (requests)
python theben-conexa-requests.py

# Experimentelle Version (httpx)
python theben-conexa-httpx.py
```

### Beispielausgabe (erfolgreich)

```
INFO:__main__:Theben Conexa HTTP Client
INFO:__main__:This is a connection test for the Theben Conexa Smart-Meter Gateway
INFO:__main__:Verwende Protokoll: https (Port 443)
INFO:__main__:Connecting to 10.11.120.2:443...
INFO:__main__:Überprüfe Erreichbarkeit von 10.11.120.2...
INFO:__main__:✓ PING erfolgreich: 10.11.120.2 ist erreichbar
INFO:__main__:✓ Zertifikat 10.11.120.2_public_cert.pem existiert bereits.
INFO:__main__:Zertifikatsanalyse:
INFO:__main__:  ✓ SAN-Name im Zertifikat: ethe0300186023.sm
INFO:__main__:  ℹ Das Zertifikat ist nur für 'ethe0300186023.sm' gültig
INFO:__main__:✓ DNS-Auflösung erfolgreich: ethe0300186023.sm → 10.11.120.2
INFO:__main__:✓ PING über ethe0300186023.sm erfolgreich
INFO:__main__:Calling: POST https://ethe0300186023.sm:443/smgw/m2m/
INFO:__main__:✓ SSL-Verifizierung aktiv mit 10.11.120.2_public_cert.pem
INFO:__main__:✓ Request-Zeit: 3.936 Sekunden
INFO:__main__:✓ Status Code: 200
INFO:__main__:✓ Firmware Version des Theben Conexa SMGW: v3.87.0-cc
```

## Sicherheitsfeatures

### TOFU (Trust On First Use)
Beim ersten Aufruf wird das SSL-Zertifikat des SMGW heruntergeladen und gespeichert. Bei allen weiteren Aufrufen wird dieses Zertifikat zur Verifizierung verwendet.

### Automatische SAN-Name-Extraktion
Das Script extrahiert automatisch den Subject Alternative Name (SAN) aus dem Zertifikat und prüft, ob dieser über DNS auflösbar ist.

### Verbindungs-Checks
- DNS-Auflösung
- PING-Test (Netzwerkerreichbarkeit)
- Timeout-Handling
- Detaillierte Fehlerdiagnose

## Abhängigkeiten

```bash
pip install requests python-dotenv
# Für httpx (optional, experimentell):
pip install httpx
```
