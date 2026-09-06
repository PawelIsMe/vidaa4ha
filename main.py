from app.mqtt_client import MQTTClient
from app.tv_client import TVClient
from app.logger import logger
from app.config import load_config
from app.ha_discovery import publish_all_discovery
from app import __version__, __author__
import signal
import time
import sys



# Ending of program
def exit_gracefully(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, exit_gracefully)
signal.signal(signal.SIGINT, exit_gracefully)



def main():
    logger.info("=========================================")
    logger.info(f"Starting Vidaa4Ha v{__version__} by {__author__}")
    logger.info("=========================================")

    # Config
    config = load_config()

    # Mqtt
    logger.info("Initializing MQTT client...")
    mqtt = MQTTClient(config['mqtt'])
    mqtt.connect()

    # Waiting for connection to mosquitto
    timeout = 10
    start = time.time()

    while not mqtt.is_connected():
        if time.time() - start > timeout:
            logger.error("MQTT connection timeout.")
            return
        time.sleep(0.1)
    logger.info("MQTT connected successfully.")

    # TV
    logger.info("Initializing TV client...")
    tv = TVClient(config['tv'], mqtt)

    if not tv.connect():
        logger.error("Cannot connect to TV. Exiting.")
        return

    logger.info("TV connected successfully.")


    # MQTT Discovery
    logger.info("Publishing MQTT Discovery...")
    publish_all_discovery(mqtt)


    # Online status
    mqtt.publish('vidaa_tv/status',"online", retain=True)
    if config.get('rapidapi', {}).get('key'):
        mqtt.publish('vidaa_tv/rapidapi/status', "online", retain=True)
    logger.info("Vidaa4Ha started successfully.")


    # Setting default values
    mqtt.publish("vidaa_tv/text/movie_title/attributes", {"result_id": 0}, retain=True)
    mqtt.publish("vidaa_tv/text/movie_url/attributes", {"result_id": 0}, retain=True)
    mqtt.publish("vidaa_tv/text/yt_url/attributes", {"result_id": 0}, retain=True)
    mqtt.publish("vidaa_tv/text/web_url/attributes", {"result_id": 0}, retain=True)
    mqtt.publish("vidaa_tv/select/fav_platform/state", "Nothing", retain=True)
    mqtt.publish("vidaa_tv/text/movie_title/state", "", retain=True)
    mqtt.publish("vidaa_tv/text/movie_url/state", "", retain=True)
    mqtt.publish("vidaa_tv/text/yt_url/state", "", retain=True)
    mqtt.publish("vidaa_tv/text/web_url/state", "", retain=True)


    # Subs
    mqtt.subscribe(f"vidaa_tv/button/set/#")
    mqtt.subscribe(f"vidaa_tv/text/movie_title/set/#")
    mqtt.subscribe(f"vidaa_tv/text/movie_url/set/#")
    mqtt.subscribe(f"vidaa_tv/text/yt_url/set/#")
    mqtt.subscribe(f"vidaa_tv/text/web_url/set/#")
    mqtt.subscribe(f"vidaa_tv/select/fav_platform/set/#")



    # Main loop
    next_check = time.monotonic()
    try:
        while True:
            if not mqtt.is_connected():
                return

            # Setting where to send topics and payloads from mqtt
            if mqtt.ha_message_received:
                tv.handle_message(mqtt.ha_message_topic, mqtt.ha_message_payload)
                mqtt.ha_message_received = False

            if time.monotonic() >= next_check:
                tv.monitor_states()
                next_check = time.monotonic() + 300

            # To avoid overloading the processor
            # time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping application...")
    finally:
        # Offline status
        mqtt.publish('vidaa_tv/status',"offline", retain=True)
        mqtt.publish('vidaa_tv/rapidapi/status', "offline", retain=True)
        tv.disconnect()
        mqtt.disconnect()
        logger.info("Application stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped.")