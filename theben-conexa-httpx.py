"""
⚠️ EXPERIMENTELL - Digest-Auth-Kompatibilitätsproblem ⚠️

Diese httpx-Version hat ein bekanntes Problem mit der Digest-Authentifizierung
beim Theben Conexa SMGW:
- Der Server schließt die Verbindung nach dem ersten Auth-Challenge (RemoteProtocolError)
- TOFU und PING-Check sind vollständig implementiert und funktionieren

✅ EMPFOHLEN: Verwenden Sie stattdessen 'theben-conexa-requests.py'
   Diese Version funktioniert zuverlässig mit dem Theben Conexa SMGW.

Status dieser Datei:
- ✓ TOFU (Trust On First Use) implementiert
- ✓ PING-Check implementiert  
- ✓ SSL-Verifizierung implementiert
- ✗ Digest-Auth nicht kompatibel mit Theben Conexa SMGW

httpx Version: 0.28.1 (neueste verfügbare Version)
"""

from dotenv import load_dotenv
import os
import httpx
import asyncio
import json
import logging
import socket
import ssl
import subprocess
import platform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

def download_certificate(ip_address, port, output_file):
    """Lädt das SSL-Zertifikat eines Servers herunter."""
    context = ssl._create_unverified_context()
    with socket.create_connection((ip_address, port)) as sock:
        with context.wrap_socket(sock, server_hostname=ip_address) as ssock:
            cert = ssock.getpeercert(binary_form=True)
            with open(output_file, "wb") as f:
                f.write(ssl.DER_cert_to_PEM_cert(cert).encode())

def get_cert_san_name(cert_path):
    """Extrahiert den SAN-Namen aus einem Zertifikat."""
    x509 = ssl._ssl._test_decode_cert(cert_path)
    if 'subjectAltName' in x509:
        for name_type, name_value in x509['subjectAltName']:
            return name_value
    return None

def check_dns_and_ping(hostname, timeout=2):
    """
    Überprüft, ob ein Hostname zu einer IP-Adresse aufgelöst werden kann und 
    ob diese IP-Adresse über PING erreichbar ist.
    
    Returns:
        tuple: (ip_address, dns_resolved, ping_successful, error_message)
    """
    ip_address = None
    dns_resolved = False
    ping_successful = False
    error_message = ""
    
    # DNS-Auflösung überprüfen
    try:
        ip_address = socket.gethostbyname(hostname)
        dns_resolved = True
    except socket.gaierror as e:
        error_message = f"DNS-Auflösungsfehler: {e}"
        return None, False, False, error_message
    
    # PING-Erreichbarkeit überprüfen
    try:
        # Betriebssystem-spezifischen PING-Befehl ausführen
        if platform.system().lower() == "windows":
            command = ["ping", "-n", "1", "-w", str(timeout * 1000), ip_address]
        else:
            command = ["ping", "-c", "1", "-W", str(timeout), ip_address]
        
        # PING ausführen mit korrektem Encoding für Windows
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            encoding='cp850' if platform.system().lower() == "windows" else 'utf-8',
            errors='ignore'
        )
        
        # Erfolgreichen PING erkennen
        if result.returncode == 0:
            ping_successful = True
        else:
            error_message = f"PING nicht erfolgreich. Return Code: {result.returncode}"
    except Exception as e:
        error_message = f"Fehler beim PING-Versuch: {e}"
    
    return ip_address, dns_resolved, ping_successful, error_message

async def main():
    logger.warning("=" * 70)
    logger.warning("⚠️  EXPERIMENTELL - Bekannte Digest-Auth-Probleme")
    logger.warning("⚠️  Verwenden Sie 'theben-conexa-requests.py' für produktive Einsätze")
    logger.warning("=" * 70)
    logger.info("Theben Conexa HTTP Client")
    logger.info("This is a connection test for the Theben Conexa Smart-Meter Gateway")
    logger.info("Connect with the HTTPX library (async)")
    logger.info(f"HTTPX Version: {httpx.__version__}")

    load_dotenv()  # .env-Datei laden

    ip_address = os.getenv("CONEXA_IP_ADDRESS", "")
    port = os.getenv("CONEXA_PORT", "")
    username = os.getenv("CONEXA_USERNAME", "")
    password = os.getenv("CONEXA_PASSWORD", "")
    
    # Protokoll automatisch basierend auf Port bestimmen
    protocol = "https" if port == "443" else "http"
    logger.info(f"Verwende Protokoll: {protocol} (Port {port})")

    logger.info(f"Connecting to {ip_address}:{port}...")

    # PING-Check vor dem eigentlichen Request
    logger.info(f"Überprüfe Erreichbarkeit von {ip_address}...")
    resolved_ip, dns_ok, ping_ok, error = check_dns_and_ping(ip_address, timeout=3)
    
    if not dns_ok:
        logger.error(f"DNS-Auflösung fehlgeschlagen: {error}")
        logger.error("Abbruch: Das Gerät kann nicht erreicht werden.")
        return
    
    if not ping_ok:
        logger.warning(f"PING fehlgeschlagen: {error}")
        logger.warning("Das Gerät antwortet nicht auf PING, versuche trotzdem HTTP-Request...")
    else:
        logger.info(f"✓ PING erfolgreich: {ip_address} ist erreichbar (IP: {resolved_ip})")
    
    # Merke die aufgelöste IP für den Vergleich
    target_ip = resolved_ip

    ####################################################
    ### Certificates (TOFU - Trust On First Use)
    ####################################################

    cert_file = f"{target_ip}_public_cert.pem"
    hostname_to_use = ip_address  # Standardmäßig den konfigurierten Namen verwenden
    verify_ssl = False  # Standard: keine Verifizierung
    
    # Nur bei HTTPS Zertifikat herunterladen und verwenden
    if protocol == "https":
        # Prüfen, ob das Zertifikat bereits existiert
        if not os.path.exists(cert_file):
            logger.info(f"Zertifikat {cert_file} nicht gefunden. Wird heruntergeladen...")
            download_certificate(target_ip, int(port), cert_file)
            logger.info(f"✓ Zertifikat wurde heruntergeladen und in {cert_file} gespeichert.")
        else:
            logger.info(f"✓ Zertifikat {cert_file} existiert bereits. Kein erneuter Download notwendig.")
        
        # SAN-Name aus Zertifikat extrahieren
        san = get_cert_san_name(cert_file)
        logger.info("Zertifikatsanalyse:")
        logger.info(f"  ✓ SAN-Name im Zertifikat: {san}")
        logger.info(f"  ℹ Das Zertifikat ist nur für '{san}' gültig")
        
        # DNS-Check für den SAN-Namen
        logger.info(f"Überprüfe DNS-Auflösung für {san}...")
        san_ip, san_dns_ok, san_ping_ok, san_error = check_dns_and_ping(san, timeout=3)
        
        if san_dns_ok and san_ip == target_ip:
            logger.info(f"✓ DNS-Auflösung erfolgreich: {san} → {san_ip}")
            if san_ping_ok:
                logger.info(f"✓ PING über {san} erfolgreich")
            hostname_to_use = san  # SAN-Namen verwenden
            verify_ssl = cert_file  # SSL-Verifizierung aktivieren
        else:
            logger.warning(f"⚠ DNS-Auflösung für {san} fehlgeschlagen oder falsche IP")
            if san_dns_ok:
                logger.warning(f"  {san} zeigt auf {san_ip}, erwartet: {target_ip}")
            logger.warning(f"  Lösung: Eintrag in Windows-Hosts-Datei hinzufügen:")
            logger.warning(f"  → {target_ip}  {san}")
            logger.warning(f"  Datei: C:\\Windows\\System32\\drivers\\etc\\hosts")
            logger.warning(f"  (Benötigt Administrator-Rechte)")
            logger.warning("")
            logger.warning(f"  Alternative: DNS-Server-Eintrag: {san} → {target_ip}")
            logger.warning(f"  Fallback: Verwende {ip_address} ohne Zertifikat-Validierung")

    # Request the smgw-info
    url = f"{protocol}://{hostname_to_use}:{port}/smgw/m2m/"

    body = {"method": "smgw-info"}
    
    headers = {
        'Content-Type': 'application/json',
    }  

    logger.info(f"Calling: POST {url}")
    logger.info(f"  with username: {username}")
    logger.info(f"  with body: {body}")

    try:
        import time
        
        # AsyncClient mit SSL-Einstellungen
        if protocol == "https" and verify_ssl:
            logger.info(f"✓ SSL-Verifizierung aktiv mit {cert_file}")
            async with httpx.AsyncClient(verify=verify_ssl) as client:
                await execute_request(client, url, username, password, body, headers)
        else:
            if protocol == "https":
                logger.warning("⚠ SSL-Verifizierung deaktiviert (Sicherheitsrisiko!)")
            async with httpx.AsyncClient(verify=False) as client:
                await execute_request(client, url, username, password, body, headers)

    except httpx.TimeoutException:
        logger.error("Timeout: Das Gerät antwortet nicht innerhalb von 10 Sekunden")
        logger.error("Mögliche Ursachen:")
        logger.error("  - Das Gerät ist überlastet oder hängt")
        logger.error("  - Die Netzwerkverbindung ist sehr langsam")
        logger.error("  - Der HTTP-Port ist nicht erreichbar")
    except httpx.ConnectError as e:
        logger.error(f"Verbindungsfehler: {e}")
        logger.error("Mögliche Ursachen:")
        logger.error("  - Das Gerät ist nicht eingeschaltet")
        logger.error("  - Das Gerät hat eine andere IP-Adresse")
        logger.error(f"  - Der Port {port} ist nicht offen oder falsch")
        logger.error("  - Eine Firewall blockiert die Verbindung")
    except httpx.RemoteProtocolError as e:
        logger.error(f"Protokollfehler: {e}")
        logger.error("Mögliche Ursachen:")
        logger.error("  - Das Gerät hat die Verbindung unerwartet geschlossen")
        logger.error("  - Digest-Authentifizierung wird möglicherweise nicht korrekt verarbeitet")
        logger.error("  - Verwenden Sie die requests-Version als Alternative")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        logger.error(f"Fehlertyp: {type(e).__name__}")

async def execute_request(client, url, username, password, body, headers):
    """Führt den HTTP-Request aus und misst die Zeit."""
    import time
    
    client.headers.update(headers)
    
    # Startzeit messen
    start_time = time.time()
    
    logger.info("Sende HTTP-Request...")
    response = await client.post(
        url,
        auth=httpx.DigestAuth(username, password),
        timeout=10.0,
        json=body,
        follow_redirects=True
    )
    
    # Endzeit messen und Differenz berechnen
    end_time = time.time()
    execution_time = end_time - start_time
    
    logger.info(f"✓ Request-Zeit: {execution_time:.3f} Sekunden")
    logger.info(f"✓ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        response_json = response.json()
        logger.info(f"✓ Firmware Version des Theben Conexa SMGW: {response_json['smgw-info']['firmware-info']['version']}")
    elif response.status_code == 401:
        logger.error("✗ Authentifizierung fehlgeschlagen (401 Unauthorized)")
        logger.error("Mögliche Ursachen:")
        logger.error("  - Benutzername oder Passwort falsch")
        logger.error("  - Digest-Auth wird vom Server nicht unterstützt")
        logger.error(f"  - Verwendeter Username: {username}")
    else:
        logger.error(f"✗ Unerwarteter Status Code: {response.status_code}")
        logger.error(f"Error Response: {response.text}")

if __name__ == '__main__':
    # Event-Loop erstellen und main() ausführen
    asyncio.run(main())