from dotenv import load_dotenv
import os
import requests
from requests.auth import HTTPDigestAuth
import socket
import ssl
import subprocess
import platform

def download_certificate(ip_address, port, output_file):
    context = ssl._create_unverified_context()
    with socket.create_connection((ip_address, port)) as sock:
        with context.wrap_socket(sock, server_hostname=ip_address) as ssock:
            cert = ssock.getpeercert(binary_form=True)
            with open(output_file, "wb") as f:
                f.write(ssl.DER_cert_to_PEM_cert(cert).encode())

def get_cert_san_name(cert_path):
    x509 = ssl._ssl._test_decode_cert(cert_path)
    #common_name = x509['subject'][0][0][1]
    if 'subjectAltName' in x509:
        for name_type, name_value in x509['subjectAltName']:
            san_name = name_value
    return san_name

def check_dns_and_ping(hostname, timeout=2):
    """
    Überprüft, ob ein Hostname zu einer IP-Adresse aufgelöst werden kann und 
    ob diese IP-Adresse über PING erreichbar ist.
    
    Args:
        hostname (str): Der zu überprüfende Hostname
        timeout (int): Timeout für den PING-Befehl in Sekunden
        
    Returns:
        tuple: (ip_address, dns_resolved, ping_successful, error_message)
            - ip_address (str): Die aufgelöste IP-Adresse oder None
            - dns_resolved (bool): True wenn DNS-Auflösung erfolgreich
            - ping_successful (bool): True wenn PING erfolgreich
            - error_message (str): Fehlermeldung falls vorhanden
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
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = f"-w {timeout * 1000}" if platform.system().lower() == "windows" else f"-W {timeout}"
        command = ["ping", param, "1", timeout_param, ip_address]
        
        # PING ausführen
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Erfolgreichen PING erkennen
        if result.returncode == 0:
            ping_successful = True
        else:
            error_message = f"PING nicht erfolgreich. Return Code: {result.returncode}"
    except Exception as e:
        error_message = f"Fehler beim PING-Versuch: {e}"
    
    return ip_address, dns_resolved, ping_successful, error_message

if __name__ == '__main__':
    import logging

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info("Theben Conexa HTTP Client")
    logger.info("This is a connection test for the Theben Conexa Smart-Meter Gateway")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Debug logging is enabled")

    load_dotenv()  # .env-Datei laden

    ip_address = os.getenv("CONEXA_IP_ADDRESS", "")
    port = os.getenv("CONEXA_PORT", "")
    username = os.getenv("CONEXA_USERNAME", "")  # Standardwert angeben, um None zu vermeiden
    password = os.getenv("CONEXA_PASSWORD", "")

    logger.info(f"Connecting to {ip_address}:{port}...")


    # Request the smgw-info
   
    ####################################################
    ### Certificates
    ####################################################

    # cert_file = f"{ip_address}_public_cert.pem"
    
    # #Prüfen, ob das Zertifikat bereits existiert
    # import os
    # if not os.path.exists(cert_file):
    #     logger.info(f"Zertifikat {cert_file} nicht gefunden. Wird heruntergeladen...")
    #     download_certificate(ip_address, port, cert_file)
    #     logger.info(f"Zertifikat wurde heruntergeladen und in {cert_file} gespeichert.")
    # else:
    #     logger.info(f"Zertifikat {cert_file} existiert bereits. Kein erneuter Download notwendig.")
    
    # san = get_cert_san_name(cert_file)
    # logger.info("Die Zertifikatsanalyse zeigt:")
    # logger.info(f"    Das Zertifikat ist gültig für diesen Namen (SAN): {san}")
    # logger.info("    Das Zertifikat wird nur erfolgreich validiert, wenn der Aufruf über diesen Namen erfolgt.")
    # logger.info(f"    Daher bitte das Gerät direkt über {san} aufrufen oder einen Alias im DNS-Server einrichten: {san}={ip_address}")
    
    # logger.info(f"Überprüfe DNS und PING für {san}...")
    # result = check_dns_and_ping(san)
    # if result[0]==ip_address:
    #     logger.info(f"DNS-Auflösung erfolgreich: {result[0]}")
    
    url = f"https://{ip_address}:{port}/smgw/m2m/"

    headers = {
                'Content-Type': 'application/json', 
    }
    body = {"method":"smgw-info"}

    logger.info(f"Calling: POST {url}")
    logger.info(f"  with username: {username}")
    logger.info(f"  with body: {body}")

    ###################################################
    ## REQUESTS
    ###################################################

    logger.info("Connect with the REQUESTS library")
    logger.info(f"REQUESTS Version: {requests.__version__}")

    try:
        import time
        
        session = requests.Session()
        session.auth = HTTPDigestAuth(username, password)
        #session.verify = cert_file  
        session.headers.update(headers) 
        
        # Startzeit messen
        start_time = time.time()
        
        # Request ausführen
        requestsResponse = session.post(url, json=body)
        
        # Endzeit messen und Differenz berechnen
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"Request-Zeit: {execution_time:.3f} Sekunden")
        logger.info(f"Status Code: {requestsResponse.status_code}")
        
        # JSON-Verarbeitung
        response_json = requestsResponse.json()
        logger.info(f"Firmware Version des Theben Conexa SMGW: {response_json['smgw-info']['firmware-info']['version']}")

    except Exception as e:
        logger.error(f"Error: {e}")


