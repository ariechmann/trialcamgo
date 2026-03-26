# TrailCam Go – Home Assistant Integration

Inoffizielle HA-Integration für Wildkameras, die mit der **TrailCam Go**-App (com.xlink.trailcamgo) gesteuert werden. Das sind typischerweise günstige Kameras von Dsoon/MAXDONE/Punvoe und ähnlichen OEM-Herstellern.

## Funktionsweise

Die Kamera kommuniziert in zwei Schritten:

1. **Bluetooth LE** – ein einmaliger `BT_Key_On`-Befehl aktiviert den integrierten WiFi-AP
2. **HTTP-API** über WiFi – alle Daten (Fotos, Videos, Status) werden per HTTP abgerufen

> ⚠️ **Netzwerk-Hinweis**: Die Kamera erstellt ihr eigenes WLAN-Netz (`Trail Cam Pro xxxx`, PW: `12345678`). Der HA-Host muss mit diesem AP verbunden sein. Für produktiven Betrieb empfiehlt sich ein **Pi mit Ethernet + separatem WiFi-Adapter** oder ein dedizierter Bridge-Rechner.

---

## Installation (HACS)

1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories
2. URL: `https://github.com/ariechmann/ha-trailcam-go` | Kategorie: Integration
3. Installieren → HA neu starten
4. Einstellungen → Geräte & Dienste → + Integration → **TrailCam Go**

## Manuelle Installation

```
custom_components/trailcam_go/ → /config/custom_components/trailcam_go/
```

---

## Entities

| Entity | Typ | Beschreibung |
|---|---|---|
| `camera.trailcam_go_latest_capture` | Camera | Thumbnail des neuesten Fotos |
| `sensor.trailcam_go_photos` | Sensor | Anzahl Fotos auf der Kamera |
| `sensor.trailcam_go_videos` | Sensor | Anzahl Videos auf der Kamera |
| `sensor.trailcam_go_status` | Sensor | `online` / `offline` |
| `sensor.trailcam_go_last_sync` | Sensor | Zeitstempel der letzten erfolgreichen Abfrage |

---

## Services

### `trailcam_go.wake_wifi`
Sendet den BLE-Befehl an die Kamera, um ihren WiFi-AP zu aktivieren.  
**Voraussetzung**: BLE-MAC in der Konfiguration angegeben, Kamera in Bluetooth-Reichweite.

### `trailcam_go.sync`
Erzwingt eine sofortige Datenabfrage.

### `trailcam_go.download_latest`
Lädt das neueste Foto nach `/config/www/trailcam_go/` herunter.  
Danach über `http://homeassistant.local:8123/local/trailcam_go/<dateiname>` erreichbar.

---

## Beispiel-Automatisierung

```yaml
# Täglich um 06:00 Uhr: Kamera aufwecken, warten, synchronisieren
automation:
  - alias: "TrailCam morgens synchronisieren"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: trailcam_go.wake_wifi
      - delay: "00:00:10"
      - service: trailcam_go.download_latest
```

---

## Bekannte HTTP-API Endpunkte

| Endpoint | Beschreibung |
|---|---|
| `GET /SetMode?Storage` | Speichermodus aktivieren (vor Dateiabfragen) |
| `GET /Storage?GetDirFileInfo` | Datei-Statistiken (Anzahl JPG/AVI) |
| `GET /Storage?GetFilePage=0&type=Photo` | Fotoliste Seite 0 |
| `GET /Storage?GetFileThumb={fid}` | JPEG-Thumbnail |
| `GET /Storage?Download={fid}` | Datei herunterladen |
| `GET /Storage?Delete={fid}` | Datei löschen |
| `GET /SetMode?PhotoCapture` | Live-Feed vorbereiten |
| `GET /Misc?PowerOff` | WiFi deaktivieren |

Kamera-IP im AP-Modus: `192.168.1.8`  
Live-Stream: `http://192.168.1.8:8221/`

---

## Credits

Protokoll reverse-engineered von [geekitguide.com](https://geekitguide.com/wifi-ble-trailcam-investigation-part-2/) (Chris Jones).
