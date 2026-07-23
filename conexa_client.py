"""
CONEXA 3.0 Smart Meter Gateway Client Library

Eine vollständige Python-Client-Bibliothek für das Theben CONEXA 3.0 Smart Meter Gateway,
die alle dokumentierten API-Endpunkte der IF_GW_CON Schnittstelle unterstützt.

Unterstützte Funktionen:
- Authentifizierung (TLS + Digest Auth)
- Gateway-Informationen abrufen
- Vertragsdaten laden
- Vertrags-Details abrufen
- Logdaten abrufen
- Messwerte abrufen
- Selbsttest auslösen

Features:
- TOFU (Trust On First Use) für SSL-Zertifikate
- Automatische Erreichbarkeitsprüfung
- Type Hints und Dataclasses
- Umfassendes Error Handling
- Logging-Unterstützung
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import os
import json
import logging
import socket
import ssl
import subprocess
import platform
import urllib3

import requests
from requests.auth import HTTPDigestAuth

# SSL-Warnungen unterdrücken (nur für Entwicklung)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class ConexaClientError(Exception):
    """Basis-Exception für alle Conexa-Client-Fehler."""
    pass


class ConexaAuthenticationError(ConexaClientError):
    """Fehler bei der Authentifizierung."""
    pass


class ConexaNetworkError(ConexaClientError):
    """Netzwerk-bezogene Fehler."""
    pass


class ConexaAPIError(ConexaClientError):
    """API-bezogene Fehler."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# ============================================================================
# Enums
# ============================================================================

class DatabaseType(str, Enum):
    """Messwertlisten-Typen."""
    ORIGIN = "origin"  # Originäre Messwertliste
    DERIVED = "derived"  # Abgeleitete Messwertliste
    CALCULATED = "calculated"  # Tarifumschaltmesswertliste (nur TAF2)
    DAILY = "daily"  # Tageswerte


class LogLevel(int, Enum):
    """Log-Level gemäß Schnittstellenbeschreibung."""
    INFORMATIONAL = 1
    WARNING = 2
    ERROR = 3
    ALERT = 4


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class FirmwareInfo:
    """Firmware-Informationen des Gateways."""
    component: str
    version: str
    hash: str


@dataclass
class Certificate:
    """Zertifikatsinformationen."""
    cert_index: Optional[str] = None
    tls: Optional[str] = None  # HAN TLS-Zertifikat
    sig: Optional[str] = None  # Signatur-Zertifikat
    sub_ca: Optional[str] = None  # SubCA-Zertifikat


@dataclass
class SmgwInfo:
    """Smart Meter Gateway Informationen."""
    smgw_id: str
    smgw_state: str
    smgw_time: str
    firmware_info: FirmwareInfo
    certificates: Dict[str, Any]


@dataclass
class BillingPeriod:
    """Abrechnungsperiode."""
    start_time: str
    end_time: str


@dataclass
class Meter:
    """Zähler-Informationen."""
    meter_id: str


@dataclass
class UsagePoint:
    """Tarifanwendungsfall (Usage Point)."""
    usage_point_id: str
    usage_point_name: str
    metering_point_id: str
    taf_number: str
    taf_state: str
    start_time: str
    end_time: str
    capture_time: str
    delivery_id: str
    on_demand_profile_configured: str
    billing_periods: List[BillingPeriod]
    meter: List[Meter]


@dataclass
class Channel:
    """Messkanal-Informationen."""
    obis: str
    scaler: str
    unit: str


@dataclass
class UsagePointInfo:
    """Detaillierte Informationen eines Tarifanwendungsfalls."""
    usage_point_id: str
    usage_point_name: str
    taf_profile: str
    transparency_bit: str
    emts: List[str]
    databases: List[Dict[str, Any]]


@dataclass
class LogEntry:
    """Logbuch-Eintrag."""
    index: str
    record_number: str
    event_id: str
    event_sub_id: str
    level: str
    outcome: str
    vendor_id: str
    subject_identity: str
    user_identity: str
    time: str
    message: str
    version: str


@dataclass
class Reading:
    """Messwert-Eintrag."""
    capture_time: str
    target_time: str
    value: str
    cosem_status: str
    meter_status: str
    smgw_status: str
    owner_number: str
    signature: Optional[str] = None


@dataclass
class ChannelReadings:
    """Messwerte für einen Kanal."""
    obis: str
    readings: List[Reading]


# ============================================================================
# Main Client
# ============================================================================

class ConexaClient:
    """
    Client für das CONEXA 3.0 Smart Meter Gateway.
    
    Unterstützt alle dokumentierten API-Endpunkte der IF_GW_CON Schnittstelle.
    
    Beispiel:
        >>> client = ConexaClient(
        ...     ip_address="192.168.1.100",
        ...     port=443,
        ...     username="user",
        ...     password="pass"
        ... )
        >>> client.connect()
        >>> info = client.get_gateway_info()
        >>> print(info.smgw_id)
    """
    
    def __init__(
        self,
        ip_address: str,
        port: int = 443,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cert_file: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 10
    ):
        """
        Initialisiert den Conexa-Client.
        
        Args:
            ip_address: IP-Adresse oder Hostname des Gateways
            port: Port (Standard: 443 für HTTPS)
            username: Benutzername für Digest-Auth (optional)
            password: Passwort für Digest-Auth (optional)
            cert_file: Pfad zum SSL-Zertifikat (optional, wird automatisch heruntergeladen)
            verify_ssl: SSL-Verifizierung aktivieren
            timeout: Request-Timeout in Sekunden
        """
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Protokoll basierend auf Port bestimmen
        self.protocol = "https" if port == 443 else "http"
        self.base_url = f"{self.protocol}://{ip_address}:{port}"
        
        # Session für persistente Verbindungen
        self.session = requests.Session()
        
        # Digest-Auth konfigurieren, wenn Credentials vorhanden
        if username and password:
            self.session.auth = HTTPDigestAuth(username, password)
        
        # Zertifikat-Handling
        self.cert_file = cert_file or f"{ip_address}_public_cert.pem"
        
        # User-ID wird nach erfolgreicher Anmeldung gesetzt
        self.user_id: Optional[str] = None
        
        logger.info(f"ConexaClient initialisiert für {self.base_url}")
    
    # ========================================================================
    # Connection & Setup
    # ========================================================================
    
    def check_connectivity(self, timeout: int = 3) -> Tuple[bool, str]:
        """
        Überprüft die Erreichbarkeit des Gateways via DNS und PING.
        
        Args:
            timeout: Timeout für PING in Sekunden
            
        Returns:
            Tuple aus (erfolg, fehlermeldung)
        """
        logger.info(f"Überprüfe Erreichbarkeit von {self.ip_address}...")
        
        # DNS-Auflösung
        try:
            resolved_ip = socket.gethostbyname(self.ip_address)
            logger.info(f"✓ DNS-Auflösung erfolgreich: {self.ip_address} -> {resolved_ip}")
        except socket.gaierror as e:
            error_msg = f"DNS-Auflösung fehlgeschlagen: {e}"
            logger.error(error_msg)
            return False, error_msg
        
        # PING-Check
        try:
            if platform.system().lower() == "windows":
                command = ["ping", "-n", "1", "-w", str(timeout * 1000), resolved_ip]
            else:
                command = ["ping", "-c", "1", "-W", str(timeout), resolved_ip]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='cp850' if platform.system().lower() == "windows" else 'utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                logger.info(f"✓ PING erfolgreich: {resolved_ip} ist erreichbar")
                return True, ""
            else:
                error_msg = f"PING fehlgeschlagen (Return Code: {result.returncode})"
                logger.warning(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Fehler beim PING: {e}"
            logger.warning(error_msg)
            return False, error_msg
    
    def download_certificate(self, force: bool = False) -> None:
        """
        Lädt das SSL-Zertifikat des Gateways herunter (TOFU).
        
        Args:
            force: Zertifikat auch überschreiben, wenn es bereits existiert
        """
        if self.protocol != "https":
            logger.info("Kein HTTPS - Zertifikat-Download nicht erforderlich")
            return
        
        if os.path.exists(self.cert_file) and not force:
            logger.info(f"✓ Zertifikat {self.cert_file} existiert bereits")
            return
        
        logger.info(f"Lade Zertifikat von {self.ip_address}:{self.port}...")
        
        try:
            context = ssl._create_unverified_context()
            with socket.create_connection((self.ip_address, self.port)) as sock:
                with context.wrap_socket(sock, server_hostname=self.ip_address) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    with open(self.cert_file, "wb") as f:
                        f.write(ssl.DER_cert_to_PEM_cert(cert).encode())
            
            logger.info(f"✓ Zertifikat erfolgreich in {self.cert_file} gespeichert")
            
        except Exception as e:
            raise ConexaNetworkError(f"Fehler beim Zertifikat-Download: {e}")
    
    def connect(self, check_ping: bool = True) -> bool:
        """
        Stellt die Verbindung zum Gateway her und bereitet die Session vor.
        
        Args:
            check_ping: Erreichbarkeitsprüfung durchführen
            
        Returns:
            True bei erfolgreicher Verbindung
            
        Raises:
            ConexaNetworkError: Bei Netzwerkproblemen
            
        Hinweis:
            Bei diesem Gateway ist keine explizite Anmeldung erforderlich.
            Die Authentifizierung erfolgt automatisch über Digest-Auth beim ersten API-Call.
        """
        # Erreichbarkeit prüfen
        if check_ping:
            success, error = self.check_connectivity()
            if not success:
                logger.warning(f"Erreichbarkeitsprüfung fehlgeschlagen: {error}")
                logger.warning("Versuche trotzdem, Verbindung herzustellen...")
        
        # Zertifikat herunterladen (TOFU)
        if self.protocol == "https":
            self.download_certificate()
            if self.verify_ssl:
                self.session.verify = self.cert_file
                logger.info(f"✓ SSL-Verifizierung aktiv mit {self.cert_file}")
            else:
                self.session.verify = False
                logger.warning("⚠ SSL-Verifizierung deaktiviert")
        
        # User-ID wird nicht benötigt - direkt auf /smgw/m2m/ posten
        self.user_id = ""  # Leerer String als Marker, dass connect() aufgerufen wurde
        
        logger.info("✓ Verbindung vorbereitet - bereit für API-Calls")
        return True
    
    # ========================================================================
    # API Methods
    # ========================================================================
    
    def _post_json(self, method: str, **params) -> Dict[str, Any]:
        """
        Sendet einen JSON-POST-Request an die M2M-Schnittstelle.
        
        Args:
            method: Die API-Methode (z.B. "smgw-info")
            **params: Zusätzliche Parameter für den Request-Body
            
        Returns:
            Die JSON-Response als Dictionary
            
        Raises:
            ConexaAPIError: Bei API-Fehlern
        """
        if self.user_id is None:
            raise ConexaAuthenticationError("Nicht verbunden - rufen Sie zuerst connect() auf")
        
        # URL ohne user_id - das Gateway benötigt keine explizite User-ID im Pfad
        url = f"{self.base_url}/smgw/m2m/"
        
        payload = {"method": method}
        payload.update(params)
        
        headers = {"Content-Type": "application/json"}
        
        logger.debug(f"POST {url} - Method: {method}")
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=self.cert_file if self.protocol == "https" and self.verify_ssl else False
            )
            
            # Erfolgreiche Response
            if response.status_code == 200:
                return response.json()
            
            # Fehlerbehandlung
            error_messages = {
                400: "Ungültige Anfrage - Fehlerhafte Parameter",
                401: "Nicht autorisiert - Authentifizierung fehlgeschlagen",
                403: "Zugriff verweigert",
                404: "Ressource nicht gefunden",
                405: "HTTP-Methode nicht erlaubt",
                500: "Interner Server-Fehler"
            }
            
            error_msg = error_messages.get(
                response.status_code,
                f"HTTP-Fehler {response.status_code}"
            )
            
            raise ConexaAPIError(error_msg, response.status_code)
            
        except requests.exceptions.RequestException as e:
            raise ConexaNetworkError(f"Netzwerkfehler beim API-Request: {e}")
    
    def get_gateway_info(self) -> SmgwInfo:
        """
        Ruft Informationen über das Smart Meter Gateway ab.
        
        Returns:
            SmgwInfo-Objekt mit Gateway-Informationen
            
        API-Methode: smgw-info
        """
        logger.info("Rufe Gateway-Informationen ab...")
        data = self._post_json("smgw-info")
        
        info_data = data.get("smgw-info", {})
        fw_data = info_data.get("firmware-info", {})
        
        return SmgwInfo(
            smgw_id=info_data.get("smgw-id", ""),
            smgw_state=info_data.get("smgw-state", ""),
            smgw_time=info_data.get("smgw-time", ""),
            firmware_info=FirmwareInfo(
                component=fw_data.get("component", ""),
                version=fw_data.get("version", ""),
                hash=fw_data.get("hash", "")
            ),
            certificates=info_data.get("certificates", {})
        )
    
    def get_user_info(self) -> List[UsagePoint]:
        """
        Lädt die Vertragsdaten des Letztverbrauchers.
        
        Returns:
            Liste von UsagePoint-Objekten (Tarifanwendungsfälle)
            
        API-Methode: user-info
        """
        logger.info("Lade Vertragsdaten...")
        data = self._post_json("user-info")
        
        usage_points = []
        for up_data in data.get("user-info", {}).get("usage-points", []):
            usage_points.append(UsagePoint(
                usage_point_id=up_data.get("usage-point-id", ""),
                usage_point_name=up_data.get("usage-point-name", ""),
                metering_point_id=up_data.get("metering-point-id", ""),
                taf_number=up_data.get("taf-number", ""),
                taf_state=up_data.get("taf-state", ""),
                start_time=up_data.get("start-time", ""),
                end_time=up_data.get("end-time", ""),
                capture_time=up_data.get("capture-time", ""),
                delivery_id=up_data.get("delivery-id", ""),
                on_demand_profile_configured=up_data.get("on-demand-profile-configured", ""),
                billing_periods=[
                    BillingPeriod(
                        start_time=bp.get("start-time", ""),
                        end_time=bp.get("end-time", "")
                    )
                    for bp in up_data.get("billing-Periods", [])
                ],
                meter=[
                    Meter(meter_id=m.get("meter-id", ""))
                    for m in up_data.get("meter", [])
                ]
            ))
        
        return usage_points
    
    def get_usage_point_info(
        self,
        usage_point_id: str,
        database: Optional[DatabaseType] = None
    ) -> UsagePointInfo:
        """
        Ruft detaillierte Informationen eines Tarifanwendungsfalls ab.
        
        Args:
            usage_point_id: ID des Tarifanwendungsfalls
            database: Optional - spezifische Messwertliste
            
        Returns:
            UsagePointInfo-Objekt mit Details
            
        API-Methode: usage-point-info
        """
        logger.info(f"Rufe Details für Usage Point {usage_point_id} ab...")
        
        params = {"usage-point-id": usage_point_id}
        if database:
            params["database"] = database.value
        
        data = self._post_json("usage-point-info", **params)
        
        info_data = data.get("usage-point-info", {})
        
        return UsagePointInfo(
            usage_point_id=info_data.get("usage-point-id", ""),
            usage_point_name=info_data.get("usage-point-name", ""),
            taf_profile=info_data.get("taf-profile", ""),
            transparency_bit=info_data.get("transparency-bit", ""),
            emts=info_data.get("emts", []),
            databases=info_data.get("databases", [])
        )
    
    def get_log(
        self,
        fromtime: Optional[str] = None,
        totime: Optional[str] = None,
        fromindex: Optional[int] = None,
        count: Optional[int] = None
    ) -> List[LogEntry]:
        """
        Ruft Logbuch-Einträge ab.
        
        Args:
            fromtime: Startzeitpunkt (Format: YYYY-MM-DDTHH:MM:SSZ)
            totime: Endzeitpunkt (Format: YYYY-MM-DDTHH:MM:SSZ)
            fromindex: Start-Index
            count: Anzahl der Einträge (max. 1500)
            
        Returns:
            Liste von LogEntry-Objekten
            
        API-Methode: log
        
        Hinweis:
            Erlaubte Kombinationen: fromtime, totime, fromtime+totime,
            fromindex, count, fromindex+count, fromtime+count, fromtime+totime+count
        """
        logger.info("Rufe Logdaten ab...")
        
        params = {}
        if fromtime:
            params["fromtime"] = fromtime
        if totime:
            params["totime"] = totime
        if fromindex is not None:
            params["fromindex"] = fromindex
        if count is not None:
            params["count"] = min(count, 1500)  # Max. 1500 Einträge
        
        data = self._post_json("log", **params)
        
        entries = []
        for entry_data in data.get("log", {}).get("entries", []):
            entries.append(LogEntry(
                index=entry_data.get("index", ""),
                record_number=entry_data.get("record-number", ""),
                event_id=entry_data.get("event-id", ""),
                event_sub_id=entry_data.get("event-sub-id", ""),
                level=entry_data.get("level", ""),
                outcome=entry_data.get("outcome", ""),
                vendor_id=entry_data.get("vendor-id", ""),
                subject_identity=entry_data.get("subject-identity", ""),
                user_identity=entry_data.get("user-identity", ""),
                time=entry_data.get("time", ""),
                message=entry_data.get("message", ""),
                version=entry_data.get("version", "")
            ))
        
        return entries
    
    def get_readings(
        self,
        usage_point_id: str,
        database: DatabaseType,
        channels: Optional[List[str]] = None,
        last_reading: bool = False,
        fromtime: Optional[str] = None,
        totime: Optional[str] = None
    ) -> List[ChannelReadings]:
        """
        Ruft Messwerte ab.
        
        Args:
            usage_point_id: ID des Tarifanwendungsfalls
            database: Messwertliste (origin, derived, calculated, daily)
            channels: Optional - Liste von OBIS-Codes (z.B. ["0100010800ff"])
            last_reading: Nur letzten Wert abrufen
            fromtime: Startzeitpunkt (Format: YYYY-MM-DDTHH:MM:SSZ)
            totime: Endzeitpunkt (Format: YYYY-MM-DDTHH:MM:SSZ)
            
        Returns:
            Liste von ChannelReadings-Objekten
            
        API-Methode: readings
        
        Hinweis:
            Max. Zeitraum zwischen fromtime und totime: 31 Tage
        """
        logger.info(f"Rufe Messwerte für {usage_point_id} ab...")
        
        params = {
            "usage-point-id": usage_point_id,
            "database": database.value,
            "last-reading": last_reading
        }
        
        if channels:
            params["channels"] = [{"channel": ch} for ch in channels]
        
        if not last_reading:
            if fromtime:
                params["fromtime"] = fromtime
            if totime:
                params["totime"] = totime
        
        data = self._post_json("readings", **params)
        
        channel_readings = []
        for channel_data in data.get("readings", {}).get("channels", []):
            readings = []
            for reading_data in channel_data.get("readings", []):
                readings.append(Reading(
                    capture_time=reading_data.get("capture-time", ""),
                    target_time=reading_data.get("target-time", ""),
                    value=reading_data.get("value", ""),
                    cosem_status=reading_data.get("cosem-status", ""),
                    meter_status=reading_data.get("meter-status", ""),
                    smgw_status=reading_data.get("smgw-status", ""),
                    owner_number=reading_data.get("owner-number", ""),
                    signature=reading_data.get("signature")
                ))
            
            channel_readings.append(ChannelReadings(
                obis=channel_data.get("obis", ""),
                readings=readings
            ))
        
        return channel_readings
    
    def trigger_self_test(self) -> bool:
        """
        Löst einen Selbsttest des Gateways aus.
        
        Returns:
            True bei Erfolg
            
        API-Methode: self-test
        
        Hinweis:
            Kann nur alle 10 Minuten ausgeführt werden.
            Ergebnis wird im Logbuch eingetragen.
        """
        logger.info("Löse Selbsttest aus...")
        
        try:
            self._post_json("self-test")
            logger.info("✓ Selbsttest erfolgreich ausgelöst")
            return True
        except ConexaAPIError as e:
            if e.status_code == 403:
                logger.warning("Selbsttest kann nur alle 10 Minuten ausgeführt werden")
            raise
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def close(self) -> None:
        """Schließt die Session und gibt Ressourcen frei."""
        if self.session:
            self.session.close()
            logger.info("Client-Session geschlossen")
    
    def __enter__(self):
        """Context Manager Support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Support."""
        self.close()
    
    def __repr__(self) -> str:
        return f"ConexaClient(ip={self.ip_address}, port={self.port}, connected={self.user_id is not None})"


# ============================================================================
# Convenience Functions
# ============================================================================

def create_client_from_env() -> ConexaClient:
    """
    Erstellt einen ConexaClient aus Umgebungsvariablen.
    
    Benötigte Umgebungsvariablen:
        - CONEXA_IP_ADDRESS: IP-Adresse des Gateways
        - CONEXA_PORT: Port (optional, Standard: 443)
        - CONEXA_USERNAME: Benutzername (optional)
        - CONEXA_PASSWORD: Passwort (optional)
    
    Returns:
        Konfigurierter ConexaClient
        
    Raises:
        ValueError: Wenn erforderliche Umgebungsvariablen fehlen
    """
    ip_address = os.getenv("CONEXA_IP_ADDRESS")
    if not ip_address:
        raise ValueError("Umgebungsvariable CONEXA_IP_ADDRESS nicht gesetzt")
    
    port = int(os.getenv("CONEXA_PORT", "443"))
    username = os.getenv("CONEXA_USERNAME")
    password = os.getenv("CONEXA_PASSWORD")
    
    return ConexaClient(
        ip_address=ip_address,
        port=port,
        username=username,
        password=password
    )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # Beispiel-Verwendung
    print("CONEXA 3.0 Smart Meter Gateway Client")
    print("=" * 50)
    
    # Client aus Umgebungsvariablen erstellen
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        client = create_client_from_env()
        
        # Verbindung herstellen
        client.connect()
        print(f"\n✓ Erfolgreich verbunden")
        
        # Gateway-Informationen abrufen
        print("\n1. Gateway-Informationen:")
        print("-" * 50)
        info = client.get_gateway_info()
        print(f"Gateway-ID: {info.smgw_id}")
        print(f"Status: {info.smgw_state}")
        print(f"Firmware: {info.firmware_info.version}")
        print(f"Zeit: {info.smgw_time}")
        
        # Vertragsdaten abrufen
        print("\n2. Vertragsdaten:")
        print("-" * 50)
        usage_points = client.get_user_info()
        for up in usage_points:
            print(f"  - {up.usage_point_name} (TAF {up.taf_number})")
            print(f"    ID: {up.usage_point_id}")
            print(f"    Status: {up.taf_state}")
        
        # Logdaten abrufen (letzte 10 Einträge)
        print("\n3. Letzte Logeinträge:")
        print("-" * 50)
        log_entries = client.get_log(count=10)
        for entry in log_entries[-5:]:  # Nur die letzten 5 anzeigen
            print(f"  [{entry.time}] Event {entry.event_id}: {entry.message[:60]}...")
        
        client.close()
        print("\n✓ Client erfolgreich geschlossen")
        
    except Exception as e:
        logger.error(f"Fehler: {e}")
        raise
