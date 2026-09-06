from pyvidaa import VidaaTV
from app.logger import logger
from app.api_request import APIRequest
import threading
import time
import re


class TVClient:
    def __init__(self, config: dict, mqtt):
        self._config = config
        self._connected = False
        self._tv = VidaaTV(host=config['host'], port=config.get('port', '36669'), mac_address=config['mac_address'], use_dynamic_auth=True)


        # Mqtt
        self._mqtt = mqtt

        # Topics and payloads
        self.fav_platform = "Nothing"

        # Monitor States
        self.state_type = None
        self.app_name = None
        self.app_id = None
        self.volume_level = None
        self.is_on = None
        self.is_muted = None


        # APIRequest Class
        self._apiRequest = None


        # Result IDs for attributes to homeassistant
        self.movie_result_id = 0
        self.url_movie_result_id = 0
        self.youtube_result_id = 0
        self.browser_result_id = 0



    # ===[ Connection ]===
    def connect(self):
        logger.info("Connecting to TV...")
        self._connected = self._tv.connect()
        if self._connected:
            logger.info("Connected.")
        else:
            logger.error("Connection failed.")
        return self._connected

    def disconnect(self):
        logger.info("Disconnecting from TV...")
        self._tv.disconnect()
        self._connected = False

    def is_connected(self):
        return self._connected

    # ===[ Handle message ]===
    def handle_message(self, topic: str, payload: str):
        logger.info(f"MQTT: {topic} -> {payload}")

        entities = {
            # Nav buttons
            "POWER": self._tv.power,
            "HOME": self._tv.home,
            "BACK": self._tv.back,
            "MENU": self._tv.menu,
            "OK": self._tv.ok,
            "UP": self._tv.up,
            "DOWN": self._tv.down,
            "LEFT": self._tv.left,
            "RIGHT": self._tv.right,
            "EXIT": self._tv.exit,
            "VOLUME_UP": self._tv.volume_up,
            "VOLUME_DOWN": self._tv.volume_down,
            "MUTE": self._tv.mute,
            # Apps
            "YOUTUBE": lambda: self._tv.launch_app("youtube"),
            "NETFLIX": lambda: self._tv.launch_app("netflix"),
            "DISNEY_PLUS": lambda: self._tv.launch_app("disney"),
            "PRIME_VIDEO": lambda: self._tv.launch_app("amazon"),
            # TODO spotify, browser, set_volume
        }

        if topic == "vidaa_tv/button/set":
            action = entities.get(payload, lambda: logger.info(f"Command '{payload}' doesn't exist"))
            action()
        elif topic == "vidaa_tv/select/fav_platform/set":
            self.fav_platform = payload or "Nothing"
        elif topic == "vidaa_tv/text/movie_title/set":
            # Input and selector reset
            self._mqtt.publish("vidaa_tv/text/movie_title/state", "", retain=True)
            self._mqtt.publish("vidaa_tv/select/fav_platform/state", "Nothing", retain=True)

            # Playing a movie async (other thread)
            threading.Thread(target=self.movie_by_title, args=(payload, self.fav_platform), daemon=True).start()
        elif topic == "vidaa_tv/text/movie_url/set":
            # Input reset
            self._mqtt.publish("vidaa_tv/text/movie_url/state", "", retain=True)

            # Playing a movie async (other thread)
            threading.Thread(target=self.movie_by_url, args=(payload,), daemon=True).start()
        elif topic == "vidaa_tv/text/yt_url/set":
            # Input reset
            self._mqtt.publish("vidaa_tv/text/yt_url/state", "", retain=True)

            # Playing a movie async (other thread)
            threading.Thread(target=self.turn_on_yt_video, args=(payload,), daemon=True).start()
        elif topic == "vidaa_tv/text/web_url/set":
            # Input reset
            self._mqtt.publish("vidaa_tv/text/web_url/state", "", retain=True)

            # Playing a movie async (other thread)
            threading.Thread(target=self.search_browser, args=(payload,), daemon=True).start()
        else:
            logger.info(f"Topic '{topic}' doesn't exist")


    # ===[ States Monitor ]===
    def monitor_states(self):
        # TV Statetype
        get_state = self._tv.get_state() or {}
        self.state_type = get_state.get("statetype") or "No statetype"
        self.app_name = get_state.get("name") or "No name"
        self.app_id = get_state.get("appId") or "No ID"

        # Get volume
        self._tv.get_volume()
        vol = self._tv.get_tv_info() or {}
        self.volume_level = vol.get("volume_value") or "No volume (error)"

        # Is on?
        self.is_on = self._tv.is_on()

        # Is muted?
        self.is_muted = self._tv._cached_muted

        try:
            # Publishing
            self._mqtt.publish("vidaa_tv/state/state_type", self.state_type, retain=True)
            self._mqtt.publish("vidaa_tv/state/app_name", self.app_name, retain=True)
            self._mqtt.publish("vidaa_tv/state/app_id", self.app_id, retain=True)
            self._mqtt.publish("vidaa_tv/state/volume", self.volume_level, retain=True)
            self._mqtt.publish("vidaa_tv/state/power", self.is_on, retain=True)
            self._mqtt.publish("vidaa_tv/state/mute", self.is_muted, retain=True)
            logger.info(f"Monitor: State type: {self.state_type}, App name: {self.app_name}, Volume: {self.volume_level}, Is on?: {self.is_on}, Is muted?: {self.is_muted}")
        except Exception:
            logger.exception("Cannot read TV states")

    # ===[ Turning On Methods ]===
    def turn_on_movie(self, platform, title, movie_id):
        # Needed variables update
        self.monitor_states()

        # Most optimized
        if (not self.is_on and platform == "Disney+") or self.state_type == "app":
            self._tv.home()
            time.sleep(2)

        if platform == "Netflix":
            self._tv._publish(f"/remoteapp/tv/ui_service/{self._tv.client_id}/actions/launchapp",{"appId": "1", "name": f"{title}", "url": f"m={movie_id}"})
            time.sleep(10)
            self._tv.ok()
        elif platform == "Disney+":
            self._tv._publish(f"/remoteapp/tv/ui_service/{self._tv.client_id}/actions/launchapp",{"appId": "295", "name": f"{title}", "url": f"https://cd-dmgz.bamgrid.com/bbd/hisense_tv/index.html#deeplink?page=browse&id={movie_id}&placement=vidaa-voice&placementDetail=search&distributionPartner=hisense_vidaa"})
            time.sleep(20)
            self._tv.ok()
        elif platform == "Prime Video":
            self._tv._publish(f"/remoteapp/tv/ui_service/{self._tv.client_id}/actions/launchapp",{"appId": "2", "name": f"{title}", "url": f"--deepLinkParameter={movie_id}"})
            time.sleep(10)
            self._tv.ok()
            time.sleep(15)
            self._tv.ok()


        logger.info(f"The {platform} video was successfully uploaded!")


    def movie_by_title(self, title, fav_platform):
        # Adding result ID
        self.movie_result_id += 1

        # Creating APIRequest object
        self._apiRequest = APIRequest(title, fav_platform)
        if not (movie_data := self._apiRequest.get_movie_data()):
            self._mqtt.publish("vidaa_tv/text/movie_title/attributes", {"result_id": self.movie_result_id, "found": False, "cause": f"'{title}' movie not found"}, retain=True)
            logger.info(f"'{title}' movie not found")
            return

        movie_title = movie_data[0]
        release_year = movie_data[1]
        platform_name = movie_data[2]
        movie_url = movie_data[3]
        movie_id = self.detect_and_extract_media(movie_url)[1]



        # Ha Feedback
        self._mqtt.publish("vidaa_tv/state/last_movie", f"{movie_title} ({release_year}), {platform_name}", retain=True)
        self._mqtt.publish("vidaa_tv/text/movie_title/attributes", { "result_id": self.movie_result_id, "found": True, "title": movie_title, "year": release_year, "platform": platform_name }, retain=True)

        # Logger feedback
        logger.info(f"Result ID: {self.movie_result_id}")
        logger.info(f"Movie Title: {movie_title}")
        logger.info(f"Release Year: {release_year}")
        logger.info(f"Platform Name: {platform_name}")
        logger.info(f"Movie URL: {movie_url}")
        logger.info(f"Movie ID: {movie_id}")

        # Turning on the movie
        self.turn_on_movie(platform_name, movie_title, movie_id)


    def movie_by_url(self, url):
        # Adding number to result ID
        self.url_movie_result_id += 1

        # Checking if url is correct
        if not (movie_data := self.detect_and_extract_media(url)):
            self._mqtt.publish("vidaa_tv/text/movie_title/attributes", {"result_id": self.url_movie_result_id, "found": False}, retain=True)
            logger.info(f"Movie not found")
            return

        # Getting data from url
        platform_name = movie_data[0]
        movie_id = movie_data[1]

        # Ha Feedback
        self._mqtt.publish("vidaa_tv/state/last_movie", f"ID: {movie_id}, {platform_name}", retain=True)
        self._mqtt.publish("vidaa_tv/text/movie_title/attributes", {"result_id": self.url_movie_result_id, "found": True}, retain=True)

        # Turning on the movie
        self.turn_on_movie(platform_name, "movie", movie_id)

    def turn_on_yt_video(self, url):
        # Adding number to result ID
        self.youtube_result_id += 1

        # Checking if url is correct
        url = url.strip()
        if not url.startswith("https://"):
            self._mqtt.publish("vidaa_tv/text/yt_url/attributes", {"result_id": self.youtube_result_id, "found": False, "cause": "Wrong URL"}, retain=True)
            logger.info("Youtube video not uploaded! (wrong URL)")
            return

        # Transformation link if needed
        if self.is_short_yt_url(url):
            url = self.convert_yt_url(url)

        # Turning on the yt video
        self._tv._publish(f"/remoteapp/tv/ui_service/{self._tv.client_id}/actions/launchapp", {"appId": "3", "name": "YouTube", "url": f"{url}"})


        # Ha and logger feedback
        self._mqtt.publish("vidaa_tv/text/yt_url/attributes", {"result_id": self.youtube_result_id, "found": True, "url": f"{url}"}, retain=True)
        logger.info("Youtube video uploaded successfully!")

    def search_browser(self, url):
        # Needed variables update
        self.monitor_states()

        if not self.is_on:
            self._tv.power_on()
            time.sleep(3)

        # Adding number to result ID
        self.browser_result_id += 1

        # Checking if url is correct
        url = url.strip()
        if not url.startswith(("https://", "http://")):
            self._mqtt.publish("vidaa_tv/text/web_url/attributes", {"result_id": self.browser_result_id, "found": False, "cause": "Wrong URL"}, retain=True)
            logger.info("Page not loaded! (wrong URL)")
            return

        # Turning on the page on browser
        self._tv._publish(f"/remoteapp/tv/ui_service/{self._tv.client_id}/actions/launchapp", {"appId": "16", "name": "tv browser", "url": f"{url}"})

        # Ha and logger feedback
        self._mqtt.publish("vidaa_tv/text/web_url/attributes", {"result_id": self.browser_result_id, "found": True, "url": f"{url}"}, retain=True)
        logger.info("Page loaded!")



    # ===[ Helper Methods ]===
    def detect_and_extract_media(self, link: str) -> tuple[str, str]:
        clean_link = link.strip()
        link_lower = clean_link.lower()

        if not clean_link.startswith(("https://", "http://")):
            return False

        # Disney+
        if "disneyplus" in link_lower or "disney" in link_lower:
            media_id = clean_link.rstrip("/").split("/")[-1]
            return ("Disney+", media_id)
        # Netflix
        elif "netflix" in link_lower:
            match = re.search(r"/title/(\d+)", clean_link)
            media_id = match.group(1) if match else clean_link.rstrip("/").split("/")[-1]
            return ("Netflix", media_id)
        # Prime Video
        elif "primevideo" in link_lower or "prime" in link_lower:
            if "detail" in clean_link:
                media_id = clean_link[clean_link.find("detail"):]
            else:
                media_id = clean_link
            return ("Prime Video", media_id)
        return False

    def is_short_yt_url(self, link: str) -> bool:
        """Sprawdza wyłącznie regexem, czy link jest w domenie /youtu.be"""
        return bool(re.search(r"https?://(?:www\.)?youtu\.be/", link))

    def convert_yt_url(self, link: str) -> str:
        """Przekształca link z youtu.be na format www.youtube.com z odpowiednią kolejnością parametrów."""
        # Pattern wyciąga:
        # 1. ID filmu (wszystko po / do ? lub końca)
        # 2. Parametry z query stringa (wszystko po ?)
        pattern = r"https?://(?:www\.)?youtu\.be/([^?]+)(?:\?(.*))?"
        match = re.match(pattern, link.strip())

        if not match:
            return link

        video_id = match.group(1)
        query_params = match.group(2)

        # Budujemy nowy link
        if query_params:
            return f"https://www.youtube.com/watch?{query_params}&v={video_id}&feature=youtu.be"
        else:
            return f"https://www.youtube.com/watch?v={video_id}&feature=youtu.be"
