from app.config import load_config
from app.logger import logger
import requests


class APIRequest:
    def __init__(self, title, fav_platform):
        config = load_config()
        rapidapi = config['rapidapi']
        key = rapidapi['key']

        self.title = title
        self.fav_platform = fav_platform
        # TODO because some movies or series dont returns from api
        # self.show_type = "movie"  # Optional: 'movie' or 'series'
        self.url = "https://streaming-availability.p.rapidapi.com/shows/search/title"

        self.querystring = {
            "series_granularity": "show",
            # "show_type": self.show_type,
            "output_language": "en",
            "country": "pl",
            "title": title
        }

        self.headers = {
            "x-rapidapi-key": key,
            "x-rapidapi-host": "streaming-availability.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        # TODO writes if the api key is wrong
        self.response = requests.get(self.url, headers=self.headers, params=self.querystring)
        self.data = self.response.json()



    def get_movie_data(self):
        if self.data:
            movie_data = self.data[0]
            title = movie_data.get("title", "No title")
            releaseYear = movie_data.get("releaseYear", "No year")
            final_data = [title, releaseYear]

            pl_options = movie_data.get("streamingOptions", {}).get("pl", [])

            # Dict for grouping
            available_platforms = {}


            for option in pl_options:
                service_name = option.get("service", {}).get("name")
                offer_type = option.get("type")

                if offer_type == "subscription" and (service_name == "Disney+" or service_name == "Netflix" or service_name == "Prime Video"):
                    service_name = option.get("service", {}).get("name")
                    link = option.get("link")

                    # Saving to dict if exists
                    if service_name and link and service_name not in available_platforms:
                        available_platforms[service_name] = link

            # Returns fav platform if it was chosen
            if self.fav_platform in available_platforms:
                final_data.extend([self.fav_platform, available_platforms[self.fav_platform]])
            elif available_platforms:
                platform_name, platform_link = next(iter(available_platforms.items()))
                final_data.extend([platform_name, platform_link])
            else:
                return None
            return final_data
        else:
            return None