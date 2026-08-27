from app.logger import logger
import yaml
import sys


def load_config():
    # Attempting to open and load a config file
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
            if config is None:
                raise ValueError("File is empty")
    except FileNotFoundError:
        logger.error("There is no file 'config.yaml' in main folder!")
        logger.warning("You have to complete the file according to README.md")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error parsing file 'config.yaml': {e}")
        sys.exit(1)

    # Required fields in config.yaml
    required_fields = [
        ("mqtt", "host"),
        ("mqtt", "port"),
        ("tv", "host"),
        ("tv", "port"),
        ("tv", "mac_address"),
    ]

    if config.get('mqtt', {}).get('login_required'):
        required_fields.append(("mqtt", "username"))
        required_fields.append(("mqtt", "password"))

    missing_fields = []

    # Checking fields if exist
    for section, key in required_fields:
        section_dict = config.get(section)
        if not isinstance(section_dict, dict) or section_dict.get(key) is None:
            missing_fields.append(f"{section} -> {key}")

    # Displaying an error with missing fields
    if missing_fields:
        logger.error("Incorrect configuration!")
        for field in missing_fields:
            logger.warning(f"  - Complete the field: {field}")
        sys.exit(1)
    return config