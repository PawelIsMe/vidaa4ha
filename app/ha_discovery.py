import json
import logging
from app.config import load_config
from app import __version__, __author__

logger = logging.getLogger(__name__)

# From Config
config = load_config()
tv_name = config['tv'].get("name", "Vidaa TV")
tv_brand = config['tv'].get("brand", "No brand")
tv_model = config['tv'].get("model", "No model")
mac_address = config['tv']['mac_address']


# Device Info
DISCOVERY_PREFIX = config['mqtt'].get("discovery_prefix", "homeassistant")
DEVICE_INFO = {
    "identifiers": [
        f"vidaa_tv_{mac_address.replace(':', '').lower()}"
    ],
    "connections": [
        [ "mac", mac_address ]
    ],
    "name": tv_name,
    "manufacturer": tv_brand,
    "model": tv_model,
    # "serial_number": "123456789",
    "sw_version": f"Vidaa4Ha v{__version__} by {__author__}",
    # "configuration_url": "http://192.168.1.100"
}

# You can add an entity to homeassistant with this command:
# mosquitto_pub -h localhost -u <your_username> -P <your_password> -t "homeassistant/sensor/AndrOBD/ecu_voltage/config" -m '{"name": "ECU voltage", "device_class": "voltage", "state_topic": "AndrOBD/ecu_voltage", "unit_of_measurement": "V"}'

# How to listen to some topic?
# mosquitto_sub -u <your_username> -P <your_password> -t "vidaa_tv/button/set"

# How to send messages?
# mosquitto_pub -u <your_username> -P <your_password> -t "vidaa_tv/state/volume" -m "23"

# Good page to search some mdi icons
# https://pictogrammers.com/library/mdi/

# Buttons
# Command topic: vidaa_tv/button/set
BUTTONS = [
    # Nav Buttons
    {"name": "Power", "icon": "mdi:power", "payload_press": "POWER"},
    {"name": "Home", "icon": "mdi:home-outline", "payload_press": "HOME"},
    {"name": "Back", "icon": "mdi:arrow-u-left-top", "payload_press": "BACK"},
    {"name": "Menu", "icon": "mdi:menu", "payload_press": "MENU"},
    {"name": "Ok", "icon": "mdi:pokeball", "payload_press": "OK"},
    {"name": "Up", "icon": "mdi:arrow-up", "payload_press": "UP"},
    {"name": "Down", "icon": "mdi:arrow-down", "payload_press": "DOWN"},
    {"name": "Left", "icon": "mdi:arrow-left", "payload_press": "LEFT"},
    {"name": "Right", "icon": "mdi:arrow-right", "payload_press": "RIGHT"},
    {"name": "Exit", "icon": "mdi:exit-to-app", "payload_press": "EXIT"},
    {"name": "Volume Up", "icon": "mdi:volume-plus", "payload_press": "VOLUME_UP"},
    {"name": "Volume Down", "icon": "mdi:volume-minus", "payload_press": "VOLUME_DOWN"},
    {"name": "Mute", "icon": "mdi:volume-off", "payload_press": "MUTE"},

    # Apps
    {"name": "Netflix", "icon": "mdi:netflix", "payload_press": "NETFLIX"},
    {"name": "YouTube", "icon": "mdi:youtube", "payload_press": "YOUTUBE"},
    {"name": "Prime Video", "icon": "mdi:application", "payload_press": "PRIME_VIDEO"},
    {"name": "Disney", "icon": "mdi:application", "payload_press": "DISNEY_PLUS"},


    # Not in pyvidaa
    # {"name": "Spotify", "icon": "mdi:spotify", "payload_press": "SPOTIFY"},
    # {"name": "Browser", "icon": "mdi:application", "payload_press": "BROWSER"},
]

# Inputs
# Command topic: vidaa_tv/text/{input['id']}/set
INPUTS = [
    {"name": "Movie Title", "icon": "mdi:format-title", "id": "movie_title", "availability_topic": "vidaa_tv/rapidapi/status"},
    {"name": "Movie URL (Optional)", "icon": "mdi:movie-search", "id": "movie_url"},
    {"name": "YouTube URL", "icon": "mdi:youtube-tv", "id": "yt_url"},
    {"name": "Browser URL", "icon": "mdi:web", "id": "web_url"},
]

# Select menus
# Command topic: vidaa_tv/select/{select_menu['id']}/set
SELECT_MENUS = [
    {"name": "Favorite Platform", "icon": "mdi:star-box", "id": "fav_platform", "options": ["Nothing", "Netflix", "Disney+", "Prime Video"], "availability_topic": "vidaa_tv/rapidapi/status"},
]

# Normal and binary sensors
# State topic: vidaa_tv/state/{convert_to_id(sensor['name'])}
SENSORS = [
    {"name": "State Type", "icon": "mdi:television-box", "sensor_type": "sensor"},
    {"name": "App Name", "icon": "mdi:television-box", "sensor_type": "sensor"},
    {"name": "App ID", "icon": "mdi:television-box", "sensor_type": "sensor"},
    {"name": "Last Movie", "icon": "mdi:movie", "sensor_type": "sensor"},
    {"name": "Volume", "icon": "mdi:volume-high", "sensor_type": "sensor", "unit_of_measurement": "%"},
    {"name": "Power", "icon": "mdi:power", "sensor_type": "sensor"},
    {"name": "Mute", "icon": "mdi:volume-mute", "sensor_type": "sensor"},
    {"name": "Status", "sensor_type": "binary_sensor", "state_topic": "vidaa_tv/status", "payload_on": "online", "payload_off": "offline", "device_class": "connectivity"},
]


def convert_to_id(x):
    return str(x).lower().replace(" ", "_")


def convert_button_to_json(button, option):
    if option == "topic": # 'topic' or 'payload'
        return f"{DISCOVERY_PREFIX}/button/vidaa_tv/{convert_to_id(button['name'])}/config"
    return json.dumps({
        "name": button['name'],
        "unique_id": "vidaa_tv"+convert_to_id(button['name']),
        "command_topic": "vidaa_tv/button/set",
        "availability_topic": "vidaa_tv/status",
        "payload_press": button['payload_press'],
        "icon": button['icon'],
        "device": DEVICE_INFO
    })

def convert_input_to_json(input, option):
    if option == "topic": # 'topic' or 'payload'
        return f"{DISCOVERY_PREFIX}/text/vidaa_tv/{input['id']}/config"
    return json.dumps({
        "name": input['name'],
        "unique_id": "vidaa_tv_"+input['id'],
        "command_topic": f"vidaa_tv/text/{input['id']}/set",
        "state_topic": f"vidaa_tv/text/{input['id']}/state",
        "availability_topic": f"{input.get('availability_topic', 'vidaa_tv/status')}",
        "json_attributes_topic": f"vidaa_tv/text/{input['id']}/attributes",
        "icon": input['icon'],
        "mode": "text",
        "min": 0,
        "max": 100,
        "optimistic": True,
        "device": DEVICE_INFO
    })

def convert_select_menu_to_json(select_menu, option):
    if option == "topic": # 'topic' or 'payload'
        return f"{DISCOVERY_PREFIX}/select/vidaa_tv/{select_menu['id']}/config"
    return json.dumps({
        "name": select_menu['name'],
        "unique_id": "vidaa_tv_"+select_menu['id'],
        "command_topic": f"vidaa_tv/select/{select_menu['id']}/set",
        "state_topic": f"vidaa_tv/select/{select_menu['id']}/state",
        "availability_topic": f"{select_menu.get('availability_topic', 'vidaa_tv/status')}",
        "options": select_menu['options'],
        "icon": select_menu['icon'],
        "optimistic": True,
        "device": DEVICE_INFO
    })

def convert_sensor_to_json(sensor, option):
    if option == "topic": # 'topic' or 'payload'
        return f"{DISCOVERY_PREFIX}/{sensor['sensor_type']}/vidaa_tv/{convert_to_id(sensor['name'])}/config"
    return json.dumps({
        "name": sensor['name'],
        "unique_id": f"vidaa_tv_{convert_to_id(sensor['name'])}",
        "state_topic": sensor.get("state_topic", f"vidaa_tv/state/{convert_to_id(sensor['name'])}"),
        **({"icon": sensor.get("icon")} if sensor.get("icon") else {}),
        "availability_topic": "vidaa_tv/status",
        "device": DEVICE_INFO,

        # Additional
        "unit_of_measurement": sensor.get("unit_of_measurement"),
        "payload_on": sensor.get("payload_on"),
        "payload_off": sensor.get("payload_off"),
        "device_class": sensor.get("device_class")
    })


def publish_buttons(mqtt):
    for button in BUTTONS:
        mqtt.publish(convert_button_to_json(button, 'topic'), convert_button_to_json(button, 'payload'), retain=True)

def publish_inputs(mqtt):
    for input in INPUTS:
        mqtt.publish(convert_input_to_json(input, 'topic'), convert_input_to_json(input, 'payload'), retain=True)

def publish_select_menus(mqtt):
    for select_menu in SELECT_MENUS:
        mqtt.publish(convert_select_menu_to_json(select_menu, 'topic'), convert_select_menu_to_json(select_menu, 'payload'), retain=True)

def publish_sensors(mqtt):
    for sensor in SENSORS:
        mqtt.publish(convert_sensor_to_json(sensor, 'topic'), convert_sensor_to_json(sensor, 'payload'), retain=True)


def publish_all_discovery(mqtt):
    publish_buttons(mqtt)
    publish_inputs(mqtt)
    publish_select_menus(mqtt)
    publish_sensors(mqtt)