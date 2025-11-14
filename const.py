DOMAIN = "rozklady_lodz"
PLATFORMS = ["sensor"]

CONF_STOP_NUMBER = "stop_number"
CONF_LINES = "lines"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ONLY_TRAMS = "only_trams"

DEFAULT_NAME = "Łódź Rozkłady"
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_ONLY_TRAMS = True

API_URL = "http://rozklady.lodz.pl/Home/GetTimetableReal"
