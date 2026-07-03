"""
Minimal settings storage. For a hackathon demo we persist the API key to a
local JSON file (gitignored) rather than a full secrets manager - documented
as a trade-off in the Solution Doc / README future work.
"""
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")


def get_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r") as f:
        return json.load(f)


def set_setting(key: str, value: str):
    settings = get_settings()
    settings[key] = value
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f)


def get_gemini_api_key():
    return get_settings().get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
