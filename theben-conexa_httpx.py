from dotenv import load_dotenv
import os
import httpx
import asyncio
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

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

    # Request the smgw-info
    url = f"http://{ip_address}:{port}/smgw/m2m/"
    url = f"http://{ip_address}:{port}/smgw/m2m/{username}.sm/json"

    body = {"method" : "smgw-info"}
    # JSON-Body serialisieren, um die exakte Größe zu berechnen
    json_body = json.dumps(body)
    body_size = len(json_body.encode('utf-8'))  # Anzahl der Bytes im UTF-8-kodierten JSON
    
      # Headers mit dem berechneten X-Content-Length
    headers = {
        'Content-Type': 'application/json',
        'X-Content-Length': str(body_size),
        'Content-Length': str(body_size)
    }  

    logging.info(f"Using username: {username}")
    logging.info(f"Using body: {body}")
    logging.info(f"POST {url}")
    
    async with httpx.AsyncClient() as client:
        client.headers.update(headers)
        
        # await verwenden, um auf das Ergebnis zu warten
        response = await client.post(
            url,
            auth=httpx.DigestAuth(username, password),
            timeout=20,
            content=json_body.encode('utf-8'),
            #json=body,
            follow_redirects=True
        )
        
        logging.info(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            logging.info(f"Response: {response.json()}")
        else:
            logging.info(f"Error: {response.text}")

if __name__ == '__main__':
    # Event-Loop erstellen und main() ausführen
    asyncio.run(main())