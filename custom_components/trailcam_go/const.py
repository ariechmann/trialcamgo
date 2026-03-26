"""Constants for TrailCam Go integration."""
DOMAIN = "trailcam_go"

# Defaults
DEFAULT_NAME = "TrailCam Go"
DEFAULT_IP = "192.168.1.8"
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60  # seconds

# Config keys
CONF_CAMERA_IP = "camera_ip"
CONF_BLE_MAC = "ble_mac"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_AUTO_DOWNLOAD = "auto_download"
CONF_MEDIA_PATH = "media_path"

# BLE
BLE_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
BLE_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
BLE_WAKE_CMD = b"BT_Key_On"
BLE_WAKE_DELAY = 5  # seconds to wait after BLE wake before HTTP polling

# HTTP API endpoints
API_SET_MODE_STORAGE = "/SetMode?Storage"
API_SET_MODE_CAPTURE = "/SetMode?PhotoCapture"
API_SET_MODE_SETUP = "/SetMode?Setup"
API_GET_DIR_INFO = "/Storage?GetDirFileInfo"
API_GET_FILE_PAGE = "/Storage?GetFilePage={page}&type={file_type}"
API_GET_THUMBNAIL = "/Storage?GetFileThumb={fid}"
API_DOWNLOAD_FILE = "/Storage?Download={fid}"
API_DELETE_FILE = "/Storage?Delete={fid}"
API_GET_MENU = "/Setup?GetMenuJson"
API_POWER_OFF = "/Misc?PowerOff"
LIVE_STREAM_PORT = 8221

# Platform names
PLATFORMS = ["sensor", "camera"]

# Services
SERVICE_WAKE_WIFI = "wake_wifi"
SERVICE_SYNC = "sync"
SERVICE_DOWNLOAD_LATEST = "download_latest"
