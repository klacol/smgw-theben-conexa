"""
Beispiele für die Verwendung der CONEXA Client-Bibliothek

Dieses Skript zeigt verschiedene Anwendungsfälle der conexa_client Bibliothek.
"""

import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from conexa_client import (
    ConexaClient,
    create_client_from_env,
    DatabaseType,
    ConexaClientError,
    ConexaAuthenticationError,
    ConexaNetworkError,
    ConexaAPIError
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Grundlegende Verwendung der Client-Bibliothek."""
    print("\n" + "=" * 70)
    print("BEISPIEL 1: Grundlegende Verwendung")
    print("=" * 70)
    
    # .env laden
    load_dotenv()
    
    # Client erstellen und verbinden
    with create_client_from_env() as client:
        # Verbindung herstellen
        client.connect()
        print(f"\n✓ Verbindung erfolgreich hergestellt")
        
        # Gateway-Informationen
        info = client.get_gateway_info()
        print(f"\nGateway: {info.smgw_id}")
        print(f"Firmware: {info.firmware_info.version}")
        print(f"Status: {info.smgw_state}")
        print(f"Zeit: {info.smgw_time}")


def example_contract_data():
    """Vertragsdaten und Details abrufen."""
    print("\n" + "=" * 70)
    print("BEISPIEL 2: Vertragsdaten und Details")
    print("=" * 70)
    
    load_dotenv()
    
    with create_client_from_env() as client:
        client.connect()
        
        # Alle Tarifanwendungsfälle abrufen
        usage_points = client.get_user_info()
        print(f"\n✓ {len(usage_points)} Tarifanwendungsfall(e) gefunden:")
        
        for up in usage_points:
            print(f"\n  📊 {up.usage_point_name}")
            print(f"     ID: {up.usage_point_id}")
            print(f"     TAF-Nummer: {up.taf_number}")
            print(f"     Status: {up.taf_state}")
            print(f"     Messpunkt: {up.metering_point_id}")
            print(f"     Gültig von: {up.start_time}")
            
            # Zähler anzeigen
            if up.meter:
                print(f"     Zähler:")
                for meter in up.meter:
                    print(f"       - {meter.meter_id}")
            
            # Abrechnungsperioden
            if up.billing_periods:
                print(f"     Abrechnungsperioden: {len(up.billing_periods)}")
                for bp in up.billing_periods[:3]:  # Nur erste 3
                    print(f"       - {bp.start_time} bis {bp.end_time}")
            
            # Detaillierte Informationen für diesen TAF
            print(f"\n  🔍 Details für {up.usage_point_name}:")
            details = client.get_usage_point_info(
                usage_point_id=up.usage_point_id,
                database=DatabaseType.ORIGIN
            )
            
            print(f"     Transparenz-Bit: {details.transparency_bit}")
            
            # Messkanäle anzeigen
            if details.databases:
                for db in details.databases:
                    if "channels" in db:
                        print(f"     Messkanäle ({db.get('database', 'unknown')}):")
                        for channel in db["channels"][:5]:  # Nur erste 5
                            print(f"       - OBIS: {channel.get('obis')}, "
                                  f"Einheit: {channel.get('unit')}, "
                                  f"Scaler: {channel.get('scaler')}")


def example_readings():
    """Messwerte abrufen."""
    print("\n" + "=" * 70)
    print("BEISPIEL 3: Messwerte abrufen")
    print("=" * 70)
    
    load_dotenv()
    
    with create_client_from_env() as client:
        client.connect()
        
        # Ersten Tarifanwendungsfall holen
        usage_points = client.get_user_info()
        if not usage_points:
            print("❌ Keine Tarifanwendungsfälle gefunden")
            return
        
        up = usage_points[0]
        print(f"\n📊 Messwerte für: {up.usage_point_name}")
        
        # Letzten Messwert abrufen
        print("\n  🔹 Letzter Messwert:")
        readings = client.get_readings(
            usage_point_id=up.usage_point_id,
            database=DatabaseType.ORIGIN,
            last_reading=True
        )
        
        for channel_reading in readings:
            print(f"\n  Kanal: {channel_reading.obis}")
            for reading in channel_reading.readings:
                print(f"    Zeitpunkt: {reading.capture_time}")
                print(f"    Wert: {reading.value}")
                print(f"    Status (SMGW): {reading.smgw_status}")
                print(f"    Status (COSEM): {reading.cosem_status}")
        
        # Messwerte für einen Zeitraum
        print("\n  🔹 Messwerte der letzten 7 Tage:")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        readings = client.get_readings(
            usage_point_id=up.usage_point_id,
            database=DatabaseType.ORIGIN,
            fromtime=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            totime=end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        
        for channel_reading in readings[:1]:  # Nur erster Kanal
            print(f"\n  Kanal: {channel_reading.obis}")
            print(f"  Anzahl Messwerte: {len(channel_reading.readings)}")
            
            # Ersten und letzten Wert anzeigen
            if channel_reading.readings:
                first = channel_reading.readings[0]
                last = channel_reading.readings[-1]
                print(f"  Erster Wert: {first.value} ({first.capture_time})")
                print(f"  Letzter Wert: {last.value} ({last.capture_time})")
                
                # Differenz berechnen
                try:
                    diff = int(last.value) - int(first.value)
                    print(f"  Verbrauch im Zeitraum: {diff}")
                except ValueError:
                    pass


def example_log_analysis():
    """Logbuch analysieren."""
    print("\n" + "=" * 70)
    print("BEISPIEL 4: Logbuch-Analyse")
    print("=" * 70)
    
    load_dotenv()
    
    with create_client_from_env() as client:
        client.connect()
        
        # Letzte 50 Logeinträge
        print("\n📋 Letzte 50 Logeinträge:")
        log_entries = client.get_log(count=50)
        
        print(f"\n✓ {len(log_entries)} Einträge abgerufen")
        
        # Nach Level gruppieren
        by_level = {}
        for entry in log_entries:
            level = entry.level
            by_level[level] = by_level.get(level, 0) + 1
        
        print("\nVerteilung nach Level:")
        level_names = {
            "1": "Informational",
            "2": "Warning",
            "3": "Error",
            "4": "Alert",
            "6": "Info"  # Manchmal verwendet
        }
        for level, count in sorted(by_level.items()):
            name = level_names.get(level, f"Level {level}")
            print(f"  {name}: {count}")
        
        # Letzte 10 Einträge anzeigen
        print("\n📝 Letzte 10 Einträge:")
        for entry in log_entries[-10:]:
            level_name = level_names.get(entry.level, f"Level {entry.level}")
            print(f"\n  [{entry.time}] {level_name}")
            print(f"  Event: {entry.event_id}-{entry.event_sub_id}")
            print(f"  Nachricht: {entry.message[:100]}")
            if len(entry.message) > 100:
                print(f"             {entry.message[100:200]}...")


def example_self_test():
    """Selbsttest auslösen."""
    print("\n" + "=" * 70)
    print("BEISPIEL 5: Selbsttest auslösen")
    print("=" * 70)
    
    load_dotenv()
    
    with create_client_from_env() as client:
        client.connect()
        
        print("\n🔧 Löse Selbsttest aus...")
        
        try:
            success = client.trigger_self_test()
            if success:
                print("✓ Selbsttest erfolgreich ausgelöst")
                print("\n💡 Tipp: Prüfen Sie das Logbuch für das Ergebnis:")
                
                # Warte kurz und hole Logeinträge
                import time
                time.sleep(2)
                
                log_entries = client.get_log(count=5)
                print("\nLetzte Logeinträge:")
                for entry in log_entries[-5:]:
                    print(f"  [{entry.time}] {entry.message[:80]}")
        
        except ConexaAPIError as e:
            if e.status_code == 403:
                print("⚠️ Selbsttest kann nur alle 10 Minuten ausgeführt werden")
            else:
                print(f"❌ Fehler: {e}")


def example_error_handling():
    """Fehlerbehandlung demonstrieren."""
    print("\n" + "=" * 70)
    print("BEISPIEL 6: Fehlerbehandlung")
    print("=" * 70)
    
    load_dotenv()
    
    # 1. Netzwerkfehler
    print("\n1️⃣ Netzwerkfehler simulieren:")
    try:
        client = ConexaClient(
            ip_address="192.0.2.1",  # TEST-NET Adresse (nicht erreichbar)
            port=443,
            username="test",
            password="test"
        )
        client.connect(check_ping=False)  # Ping-Check überspringen
    except ConexaNetworkError as e:
        print(f"  ✓ Erwarteter Netzwerkfehler: {e}")
    
    # 2. Authentifizierungsfehler
    print("\n2️⃣ Authentifizierungsfehler:")
    try:
        client = create_client_from_env()
        # Versuche API-Call ohne vorherige Authentifizierung
        client.get_gateway_info()
    except ConexaAuthenticationError as e:
        print(f"  ✓ Erwarteter Auth-Fehler: {e}")
    
    # 3. Context Manager mit Fehler
    print("\n3️⃣ Context Manager mit automatischer Bereinigung:")
    try:
        with create_client_from_env() as client:
            client.connect()
            # Simuliere Fehler
            raise ValueError("Simulierter Fehler")
    except ValueError:
        print("  ✓ Fehler behandelt, Session wurde automatisch geschlossen")


def example_all_channels():
    """Alle verfügbaren Messkanäle anzeigen."""
    print("\n" + "=" * 70)
    print("BEISPIEL 7: Alle Messkanäle anzeigen")
    print("=" * 70)
    
    load_dotenv()
    
    with create_client_from_env() as client:
        client.connect()
        
        usage_points = client.get_user_info()
        
        for up in usage_points:
            print(f"\n📊 {up.usage_point_name} (TAF {up.taf_number})")
            
            # Details für alle Datenbanken
            for db_type in [DatabaseType.ORIGIN, DatabaseType.DERIVED]:
                try:
                    details = client.get_usage_point_info(
                        usage_point_id=up.usage_point_id,
                        database=db_type
                    )
                    
                    print(f"\n  🗄️ Datenbank: {db_type.value}")
                    
                    for db in details.databases:
                        if db.get("database") == db_type.value and "channels" in db:
                            print(f"     Messkanäle:")
                            for channel in db["channels"]:
                                obis = channel.get("obis")
                                unit = channel.get("unit")
                                scaler = channel.get("scaler")
                                
                                # OBIS-Code interpretieren
                                obis_desc = interpret_obis(obis)
                                
                                print(f"       • {obis}: {obis_desc}")
                                print(f"         Einheit: {unit}, Scaler: {scaler}")
                
                except ConexaAPIError:
                    print(f"  ⚠️ Datenbank {db_type.value} nicht verfügbar")


def interpret_obis(obis_code: str) -> str:
    """
    Interpretiert gängige OBIS-Codes.
    
    Args:
        obis_code: OBIS-Code (z.B. "0100010800ff")
        
    Returns:
        Beschreibung des OBIS-Codes
    """
    obis_map = {
        "0100010800ff": "Bezug Wirkenergie gesamt",
        "0100020800ff": "Einspeisung Wirkenergie gesamt",
        "0100010700ff": "Bezug Wirkleistung aktuell",
        "0100020700ff": "Einspeisung Wirkleistung aktuell",
        "0100030800ff": "Bezug Blindenergie gesamt",
        "0100040800ff": "Einspeisung Blindenergie gesamt",
        "01001f0700ff": "Strom L1",
        "0100330700ff": "Strom L2",
        "0100470700ff": "Strom L3",
        "0100200700ff": "Spannung L1",
        "0100340700ff": "Spannung L2",
        "0100480700ff": "Spannung L3",
        "01000d0700ff": "Leistungsfaktor",
    }
    
    return obis_map.get(obis_code, "Unbekannter Messkanal")


def main():
    """Hauptfunktion - führt alle Beispiele aus."""
    print("\n" + "=" * 70)
    print("CONEXA 3.0 Client-Bibliothek - Beispiele")
    print("=" * 70)
    
    examples = [
        ("Grundlegende Verwendung", example_basic_usage),
        ("Vertragsdaten", example_contract_data),
        ("Messwerte", example_readings),
        ("Logbuch-Analyse", example_log_analysis),
        ("Selbsttest", example_self_test),
        ("Fehlerbehandlung", example_error_handling),
        ("Alle Messkanäle", example_all_channels),
    ]
    
    print("\nVerfügbare Beispiele:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    try:
        choice = input("\nWählen Sie ein Beispiel (1-7, 0 für alle): ")
        
        if choice == "0":
            # Alle Beispiele ausführen
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    print(f"\n❌ Fehler in '{name}': {e}")
                    logger.exception(e)
        else:
            # Einzelnes Beispiel ausführen
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                name, func = examples[idx]
                func()
            else:
                print("❌ Ungültige Auswahl")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        logger.exception(e)


if __name__ == "__main__":
    main()
