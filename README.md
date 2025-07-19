# API für das Theben Conexa Smart Meter Gateway (SMGW)

Dieses Repo enthält Code und Dokumentation zur Anfrage des HAN-API des Smart Meter Gateway (SMGW) der Firma Theben. Der Code basiert auf Python.

Die Datei [``theben-conexa_requests.py``](/theben-conexa_requets.py) enthält die Abfragen unter Verwendung der Python Bibliothek ``requests``.

Die Datei [``theben-conexa_httpx.py``](/theben-conexa_httpx.py) enthält die Abfragen unter Verwendung der Python Bibliothek ``httpx``.

Die API-Dokumentation findet man in der [Schnittstellenbeschreibung IF_GW_CON.pdf](https://github.com/klacol/smgw-theben-conexa/blob/main/Schnittstellenbeschreibung%20IF_GW_CON.pdf).

Zum Laden der Zugangsdaten bitte die Datei ``.env`` anlegen und wie folgt befüllen:

```shell
CONEXA_IP_ADDRESS=192.168....
CONEXA_PORT=443 (oder einen anderen Port, z.B. wenn ein Proxy dazwischen ist)
CONEXA_USERNAME=
CONEXA_PASSWORD=
```

Und dann mit Python ausführen.
