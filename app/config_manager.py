import os
from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

def load_config():
    """Load environment variables from .env file."""
    config = {}
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
    
    # Return a dict of all known keys, populated from os.environ
    keys = get_required_fields()
    for key in keys:
        config[key] = os.environ.get(key, '')
    
    return config

def save_config(data):
    """
    data: dict of key-value pairs to save to .env
    """
    # Create file if not exists
    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, 'w').close()

    for key, value in data.items():
        # Only save known keys
        if key in get_required_fields():
             # set_key updates or adds the key
            set_key(ENV_PATH, key, str(value))
            # Also update current os.environ for immediate use
            os.environ[key] = str(value)

def get_required_fields():
    return [
        "WEB_USERNAME", "WEB_PASSWORD",
        "HONEYGAIN_EMAIL", "HONEYGAIN_PASSWORD",
        "EARNAPP_UUID",
        "TRAFFMONETIZER_TOKEN",
        "PACKETSTREAM_CID",
        "REPOCKET_EMAIL", "REPOCKET_API_KEY",
        "EARNFM_TOKEN",
        "GRASS_USER", "GRASS_PASS",
        "UPROCK_TOKEN",
        "PACKETSHARE_EMAIL", "PACKETSHARE_PASSWORD",
        "DEVICE_NAME"
    ]

def get_config_sections():
    return [
        {
            "id": "dashboard-access",
            "title": "Dashboard Access",
            "subtitle": "Set the username and password used to log in.",
            "instructions": [
                "Change these from the defaults before exposing the dashboard beyond your LAN.",
                "If you forget them, edit the .env file on the server and restart the service."
            ],
            "fields": [
                {
                    "key": "WEB_USERNAME",
                    "label": "Username",
                    "placeholder": "admin",
                    "help": "Used for dashboard login.",
                    "sensitive": False
                },
                {
                    "key": "WEB_PASSWORD",
                    "label": "Password",
                    "placeholder": "admin",
                    "help": "Choose a strong password.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "device",
            "title": "Device Identity",
            "subtitle": "A friendly device name shown inside platforms and logs.",
            "instructions": [
                "Use a unique name per machine (example: box-01, pi-livingroom)."
            ],
            "fields": [
                {
                    "key": "DEVICE_NAME",
                    "label": "Device name",
                    "placeholder": "box-01",
                    "help": "Used by some platforms to label this machine.",
                    "sensitive": False
                }
            ]
        },
        {
            "id": "honeygain",
            "title": "Honeygain",
            "subtitle": "Runs the Honeygain client container.",
            "instructions": [
                "Use your Honeygain account email and password.",
                "Save, then start the honeygain service."
            ],
            "fields": [
                {
                    "key": "HONEYGAIN_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your Honeygain login email.",
                    "sensitive": False
                },
                {
                    "key": "HONEYGAIN_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your Honeygain login password.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "earnapp",
            "title": "EarnApp",
            "subtitle": "Runs the EarnApp container.",
            "instructions": [
                "Paste your EarnApp UUID here.",
                "If you haven't linked a device yet, create an account and follow EarnApp's device setup steps first."
            ],
            "fields": [
                {
                    "key": "EARNAPP_UUID",
                    "label": "UUID",
                    "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "help": "EarnApp device/account UUID.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "traffmonetizer",
            "title": "TraffMonetizer",
            "subtitle": "Runs the TraffMonetizer CLI container.",
            "instructions": [
                "Generate a token in your TraffMonetizer dashboard and paste it here."
            ],
            "fields": [
                {
                    "key": "TRAFFMONETIZER_TOKEN",
                    "label": "Token",
                    "placeholder": "tm_...",
                    "help": "TraffMonetizer token for this device.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "packetstream",
            "title": "PacketStream",
            "subtitle": "Runs the PacketStream client container.",
            "instructions": [
                "Find your CID in PacketStream settings and paste it here."
            ],
            "fields": [
                {
                    "key": "PACKETSTREAM_CID",
                    "label": "CID",
                    "placeholder": "ps_...",
                    "help": "PacketStream client identifier (CID).",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "repocket",
            "title": "Repocket",
            "subtitle": "Runs the Repocket container.",
            "instructions": [
                "Use your Repocket email and API key.",
                "If you rotate your API key, update it here and restart the service."
            ],
            "fields": [
                {
                    "key": "REPOCKET_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your Repocket login email.",
                    "sensitive": False
                },
                {
                    "key": "REPOCKET_API_KEY",
                    "label": "API key",
                    "placeholder": "rp_...",
                    "help": "API key from Repocket settings.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "earnfm",
            "title": "EarnFM",
            "subtitle": "Runs the EarnFM client container.",
            "instructions": [
                "Paste the EarnFM token for this device/account."
            ],
            "fields": [
                {
                    "key": "EARNFM_TOKEN",
                    "label": "Token",
                    "placeholder": "efm_...",
                    "help": "EarnFM token.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "grass",
            "title": "Grass",
            "subtitle": "Runs the Grass node container.",
            "instructions": [
                "Use the credentials you created for Grass."
            ],
            "fields": [
                {
                    "key": "GRASS_USER",
                    "label": "Username",
                    "placeholder": "username",
                    "help": "Grass account username.",
                    "sensitive": False
                },
                {
                    "key": "GRASS_PASS",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Grass account password.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "uprock",
            "title": "Uprock",
            "subtitle": "Runs the Uprock container.",
            "instructions": [
                "Paste your Uprock token here."
            ],
            "fields": [
                {
                    "key": "UPROCK_TOKEN",
                    "label": "Token",
                    "placeholder": "up_...",
                    "help": "Uprock token.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "packetshare",
            "title": "PacketShare",
            "subtitle": "Runs the PacketShare container.",
            "instructions": [
                "Use your PacketShare account email and password."
            ],
            "fields": [
                {
                    "key": "PACKETSHARE_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "PacketShare login email.",
                    "sensitive": False
                },
                {
                    "key": "PACKETSHARE_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "PacketShare login password.",
                    "sensitive": True
                }
            ]
        }
    ]
