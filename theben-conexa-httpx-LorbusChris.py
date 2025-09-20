from dotenv import load_dotenv
import os
import httpx
import ssl
import asyncio
import json
import logging
import subprocess
import platform

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def ping_host(host, timeout=2):
    """
    Überprüft, ob ein Host (IP-Adresse oder Hostname) über PING erreichbar ist.
    
    Args:
        host (str): Der zu überprüfende Host (IP-Adresse oder Hostname)
        timeout (int): Timeout für den PING-Befehl in Sekunden
        
    Returns:
        tuple: (ping_successful, error_message)
            - ping_successful (bool): True wenn PING erfolgreich
            - error_message (str): Fehlermeldung falls vorhanden
    """
    ping_successful = False
    error_message = ""
    
    # PING-Erreichbarkeit überprüfen
    try:
        # Betriebssystem-spezifischen PING-Befehl ausführen
        if platform.system().lower() == "windows":
            # Einfacher Ping-Befehl für Windows
            command = ["ping", host]
        else:
            # Parameter für Linux/Unix/Mac
            command = ["ping", "-c", "1", f"-W {timeout}", host]
        
        logging.info(f"Führe Ping-Befehl aus: {' '.join(command)}")
        
        # PING ausführen ohne Textkonvertierung (vermeidet UnicodeDecodeError)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        
        # Erfolgreichen PING erkennen
        if result.returncode == 0:
            ping_successful = True
            logging.info(f"Ping zu {host} erfolgreich!")
        else:
            error_message = f"PING nicht erfolgreich. Return Code: {result.returncode}"
            logging.warning(f"Ping zu {host} fehlgeschlagen. Return Code: {result.returncode}")
    except Exception as e:
        error_message = f"Fehler beim PING-Versuch: {e}"
        logging.error(f"Fehler beim Ping-Versuch: {e}")
    
    return ping_successful, error_message

async def main():
    logging.info("Theben Conexa HTTP Client")
    logging.info("This is a connection test for the Theben Conexa Smart-Meter Gateway")
    logging.info("Connect with the HTTPX library (async)")
    logging.info(f"HTTPX Version: {httpx.__version__}")

    load_dotenv()  # .env-Datei laden

    ip_address = os.getenv("CONEXA_IP_ADDRESS")
    port = int(os.getenv("CONEXA_PORT"))
    username = os.getenv("CONEXA_USERNAME")
    password = os.getenv("CONEXA_PASSWORD")

    # Ping-Test durchführen
    logging.info(f"Führe Ping-Test zur IP-Adresse {ip_address} durch...")
    ping_successful, error_message = ping_host(ip_address)
    
    if ping_successful:
        logging.info(f"Ping-Test erfolgreich: {ip_address} ist erreichbar.")
    else:
        logging.warning(f"Ping-Test fehlgeschlagen: {ip_address} ist nicht erreichbar.")
        logging.warning(f"Fehler: {error_message}")
        logging.warning("Beende das Programm...")
        return

    # Request the smgw-info
    url = f"https://{ip_address}:{port}/smgw/m2m/"

    body = {"method" : "smgw-info"}
    # JSON-Body serialisieren, um die exakte Größe zu berechnen
    json_body = json.dumps(body)
    body_size = len(json_body.encode('utf-8'))  # Anzahl der Bytes im UTF-8-kodierten JSON
    
    # Headers mit dem berechneten X-Content-Length
    headers = {
        'Content-Type': 'application/json',
        'X-Content-Length': str(body_size)
        # Content-Length wird automatisch von httpx gesetzt
    }  

    logging.info(f"Using username: {username}")
    logging.info(f"Using body: {body}")
    logging.info(f"POST {url}")

    # SSL-Behandlung abhängig von der HTTPX-Version
    if tuple(map(int, httpx.__version__.split("."))) < (0, 28):
        logging.info(f"HTTPX Version < 0.28 erkannt ({httpx.__version__}), verwende altes SSL-Handling")
        # SSL-Kontext erstellen, der keine Zertifikate überprüft
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Client mit SSL-Kontext erstellen
        client = httpx.AsyncClient(verify=ssl_context)
    else:
        logging.info(f"HTTPX Version >= 0.28 erkannt ({httpx.__version__}), verwende neues SSL-Handling")
        # Ab HTTPX 0.28 wird verify=False direkt verwendet, es gibt keinen ssl_context Parameter mehr
        client = httpx.AsyncClient(verify=False)
    
    # Headers aktualisieren
    client.headers.update(headers)
    
    try:
        # await verwenden, um auf das Ergebnis zu warten
        # Nur eine Methode zum Senden von Daten verwenden (json oder content, nicht beides)
        logging.debug("Sende POST-Request mit JSON-Daten")
        response = await client.post(
            url,
            auth=httpx.DigestAuth(username, password),
            timeout=20,
            json=body,  # Verwende nur json, nicht zusätzlich content
            follow_redirects=True
        )
        
        logging.info(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            logging.info(f"Response: {response.json()}")
        else:
            logging.info(f"Error: {response.text}")
    except httpx.ConnectError as e:
        logging.error(f"Verbindungsfehler: {e}")
        if "WRONG_VERSION_NUMBER" in str(e):
            logging.warning("Dies könnte darauf hindeuten, dass der Server HTTP statt HTTPS verwendet.")
            logging.warning("Versuchen Sie, die URL von https:// auf http:// zu ändern.")
    except Exception as e:
        logging.error(f"Fehler beim Ausführen der Anfrage: {e}")
    finally:
        # Client schließen
        await client.aclose()

if __name__ == '__main__':
    # Event-Loop erstellen und main() ausführen
    asyncio.run(main())