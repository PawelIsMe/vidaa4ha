import json
import paho.mqtt.client as mqtt
from app.logger import logger


class MQTTClient:
    def __init__(self, config: dict):
        self._config = config
        self._connected = False
        self.ha_message_received = False
        self.ha_message_topic = None
        self.ha_message_payload = None
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.get('client_id', 'vidaa4ha'))

        if config.get('login_required'):
            self._client.username_pw_set(config['username'], config['password'])

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message


    # ===[ Public methods ]===
    def connect(self):
        try:
            logger.info("Connecting to MQTT broker...")
            self._client.connect(host=self._config['host'], port=self._config['port'], keepalive=60)
            self._client.loop_start()
        except:
            logger.error("MQTT broker doesn't exist")

    def disconnect(self):
        logger.info("Disconnecting from MQTT broker...")
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic, payload, retain=False):
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        result = self._client.publish(topic, payload, retain=retain)
        logger.info(f"MQTT publish {topic}, retain={retain}, result={result.rc}")


    def subscribe(self, topic):
        logger.info(f"Subscribe: {topic}")
        self._client.subscribe(topic)

    def subscribe_many(self, topics):
        for topic in topics:
            self.subscribe(topic)

    def is_connected(self):
        return self._connected


    # ===[ MQTT Callbacks ]===
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            logger.info("Connected to MQTT broker.")
        else:
            logger.error(f"MQTT connection failed ({reason_code})")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        logger.warning("Disconnected from MQTT broker.")

    def _on_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode()
        logger.debug(f"MQTT Received [{topic}] {payload}")
        self.ha_message_received = True
        self.ha_message_topic = topic
        self.ha_message_payload = payload


