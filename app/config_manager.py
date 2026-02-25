import io
import os
import platform
import re

from dotenv import dotenv_values

from app.secret_store import decrypt, encrypt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_root() -> str:
    override = os.environ.get("MONEYTREE_CONFIG_DIR", "").strip()
    return override or PROJECT_ROOT


def _load_env_text() -> str:
    env_enc_path = os.path.join(config_root(), ".env.enc")
    env_plain_path = os.path.join(config_root(), ".env")
    if os.path.exists(env_enc_path):
        token = open(env_enc_path, "rb").read()
        plaintext = decrypt(token)
        return plaintext.decode("utf-8")
    if os.path.exists(env_plain_path):
        plaintext_text = open(env_plain_path, "r", encoding="utf-8").read()
        open(env_enc_path, "wb").write(encrypt(plaintext_text.encode("utf-8")))
        os.remove(env_plain_path)
        return plaintext_text
    return ""


def _dotenv_escape(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f"\"{escaped}\""


def _serialize_env(config: dict[str, str]) -> str:
    lines: list[str] = []
    for key in get_required_fields():
        value = str(config.get(key, ""))
        lines.append(f"{key}={_dotenv_escape(value)}")
    return "\n".join(lines) + "\n"

def load_config():
    """Load environment variables from .env file."""
    env_text = _load_env_text()
    parsed = dotenv_values(stream=io.StringIO(env_text))
    config = {key: str(parsed.get(key) or "") for key in get_required_fields()}
    if not config.get("TARGET_PLATFORM"):
        m = (platform.machine() or "").lower()
        if m in {"aarch64", "arm64"}:
            config["TARGET_PLATFORM"] = "linux/arm64"
        elif m in {"armv7l", "armv7"}:
            config["TARGET_PLATFORM"] = "linux/arm/v7"
        elif m in {"armv6l", "armv6"}:
            config["TARGET_PLATFORM"] = "linux/arm/v6"
        else:
            config["TARGET_PLATFORM"] = "linux/amd64"
    for key in [
        "HONEYGAIN_PLATFORM",
        "TRAFFMONETIZER_PLATFORM",
        "PACKETSTREAM_PLATFORM",
        "PACKETSHARE_PLATFORM",
        "REPOCKET_PLATFORM",
        "EARNFM_PLATFORM",
        "GRASS_PLATFORM",
        "MYSTERIUM_PLATFORM",
        "PAWNS_PLATFORM",
        "PROXYRACK_PLATFORM",
        "BITPING_PLATFORM",
    ]:
        if not config.get(key):
            config[key] = config["TARGET_PLATFORM"]
    if not config.get("ENABLE_LOAD_REDUCTION"):
        config["ENABLE_LOAD_REDUCTION"] = "true"
    if not config.get("LOAD_REDUCTION_TEMP_C"):
        config["LOAD_REDUCTION_TEMP_C"] = "70"
    if not config.get("LOAD_REDUCTION_CPU_PCT"):
        config["LOAD_REDUCTION_CPU_PCT"] = "90"
    if not config.get("LOAD_REDUCTION_RAM_PCT"):
        config["LOAD_REDUCTION_RAM_PCT"] = "90"
    if not config.get("LOAD_REDUCTION_RECOVER_TEMP_C"):
        config["LOAD_REDUCTION_RECOVER_TEMP_C"] = "65"
    if not config.get("LOAD_REDUCTION_RECOVER_CPU_PCT"):
        config["LOAD_REDUCTION_RECOVER_CPU_PCT"] = "80"
    if not config.get("LOAD_REDUCTION_RECOVER_RAM_PCT"):
        config["LOAD_REDUCTION_RECOVER_RAM_PCT"] = "80"
    if not config.get("LOAD_REDUCTION_INTERVAL_SEC"):
        config["LOAD_REDUCTION_INTERVAL_SEC"] = "10"
    if not config.get("LOAD_REDUCTION_TRIGGER_SEC"):
        config["LOAD_REDUCTION_TRIGGER_SEC"] = "30"
    if not config.get("LOAD_REDUCTION_RECOVER_SEC"):
        config["LOAD_REDUCTION_RECOVER_SEC"] = "60"
    if not config.get("LOAD_REDUCTION_COOLDOWN_SEC"):
        config["LOAD_REDUCTION_COOLDOWN_SEC"] = "30"
    if not config.get("PRIORITY_SERVICES"):
        config["PRIORITY_SERVICES"] = "grass,wipter,repocket,honeygain,pingpong"
    return config

def save_config(data):
    """
    data: dict of key-value pairs to save to .env
    """
    merged = load_config()
    for key, value in data.items():
        if key in get_required_fields():
            merged[key] = str(value)
            os.environ[key] = str(value)
    env_text = _serialize_env(merged)
    open(os.path.join(config_root(), ".env.enc"), "wb").write(encrypt(env_text.encode("utf-8")))


def create_temp_env_file() -> str:
    import tempfile

    env_text = _serialize_env(load_config())
    fd, path = tempfile.mkstemp(prefix="moneytree.", suffix=".env", dir=config_root())
    try:
        os.write(fd, env_text.encode("utf-8"))
    finally:
        os.close(fd)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return path

def get_required_fields():
    return [
        "WEB_USERNAME", "WEB_PASSWORD",
        "TARGET_PLATFORM",
        "ZRAM_SIZE_MB",
        "ENABLE_LOAD_REDUCTION",
        "LOAD_REDUCTION_TEMP_C",
        "LOAD_REDUCTION_CPU_PCT",
        "LOAD_REDUCTION_RAM_PCT",
        "LOAD_REDUCTION_RECOVER_TEMP_C",
        "LOAD_REDUCTION_RECOVER_CPU_PCT",
        "LOAD_REDUCTION_RECOVER_RAM_PCT",
        "LOAD_REDUCTION_INTERVAL_SEC",
        "LOAD_REDUCTION_TRIGGER_SEC",
        "LOAD_REDUCTION_RECOVER_SEC",
        "LOAD_REDUCTION_COOLDOWN_SEC",
        "PRIORITY_SERVICES",
        "HONEYGAIN_PLATFORM",
        "TRAFFMONETIZER_PLATFORM",
        "PACKETSTREAM_PLATFORM",
        "PACKETSHARE_PLATFORM",
        "REPOCKET_PLATFORM",
        "EARNFM_PLATFORM",
        "GRASS_PLATFORM",
        "MYSTERIUM_PLATFORM",
        "PAWNS_PLATFORM",
        "PROXYRACK_PLATFORM",
        "BITPING_PLATFORM",
        "HONEYGAIN_EMAIL", "HONEYGAIN_PASSWORD",
        "TRAFFMONETIZER_TOKEN",
        "PACKETSTREAM_CID",
        "PACKETSHARE_EMAIL", "PACKETSHARE_PASSWORD",
        "REPOCKET_EMAIL", "REPOCKET_API_KEY",
        "EARNFM_TOKEN",
        "GRASS_USER", "GRASS_PASS",
        "UPROCK_EMAIL", "UPROCK_PASSWORD",
        "PAWNS_EMAIL", "PAWNS_PASSWORD",
        "PROXYRACK_UUID", "PROXYRACK_API_KEY",
        "BITPING_EMAIL", "BITPING_PASSWORD", "BITPING_MFA",
        "WIPTER_EMAIL", "WIPTER_PASSWORD",
        "VNC_PASS",
        "PINGPONG_KEY",
        "PINGPONG_0G_PRIVATE_KEY",
        "PINGPONG_AIOZ_PRIV_KEY",
        "PINGPONG_GRASS_ACCESS",
        "PINGPONG_GRASS_REFRESH",
        "PINGPONG_BLOCKMESH_EMAIL",
        "PINGPONG_BLOCKMESH_PASSWORD",
        "PINGPONG_DAWN_EMAIL",
        "PINGPONG_DAWN_PASSWORD",
        "PINGPONG_HEMI_KEY",
        "WIZARDGAIN_EMAIL",
        "PEER2PROFIT_EMAIL",
        "DEVICE_NAME",
        # Enable flags
        "ENABLE_HONEYGAIN", "ENABLE_TRAFFMONETIZER",
        "ENABLE_PACKETSTREAM", "ENABLE_PACKETSHARE", "ENABLE_REPOCKET", "ENABLE_EARNFM",
        "ENABLE_GRASS", "ENABLE_MYSTERIUM", "ENABLE_PAWNS", "ENABLE_PROXYRACK", "ENABLE_BITPING", "ENABLE_WIZARDGAIN", "ENABLE_WIPTER", "ENABLE_UPROCK", "ENABLE_PEER2PROFIT", "ENABLE_PINGPONG"
    ]

def get_config_sections():
    return [
        {
            "id": "dashboard-access",
            "title": "Dashboard Access",
            "subtitle": "Set the username and password used to log in.",
            "instructions": [
                "Change these from the defaults before exposing the dashboard beyond your LAN.",
                "If you forget them, update the encrypted config file (.env.enc) and restart the service."
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
            "id": "load-reduction",
            "title": "Load Reduction",
            "subtitle": "Automatically stops non-priority services when the device is overheating and under load.",
            "instructions": [
                "If CPU temperature exceeds the threshold AND either CPU or RAM exceed thresholds, the system stops services to cool down.",
                "Once the device stabilizes, services are restarted gradually."
            ],
            "enable_key": "ENABLE_LOAD_REDUCTION",
            "fields": [
                {
                    "key": "LOAD_REDUCTION_TEMP_C",
                    "label": "Trigger temperature (°C)",
                    "placeholder": "70",
                    "help": "Start load reduction at or above this CPU temperature.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_CPU_PCT",
                    "label": "Trigger CPU (%)",
                    "placeholder": "90",
                    "help": "High CPU usage threshold used with temperature.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_RAM_PCT",
                    "label": "Trigger RAM (%)",
                    "placeholder": "90",
                    "help": "High RAM usage threshold used with temperature.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_RECOVER_TEMP_C",
                    "label": "Recover temperature (°C)",
                    "placeholder": "65",
                    "help": "Stop load reduction after temperature falls to this value.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_RECOVER_CPU_PCT",
                    "label": "Recover CPU (%)",
                    "placeholder": "80",
                    "help": "CPU usage must be at or below this to restart services.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_RECOVER_RAM_PCT",
                    "label": "Recover RAM (%)",
                    "placeholder": "80",
                    "help": "RAM usage must be at or below this to restart services.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_INTERVAL_SEC",
                    "label": "Check interval (sec)",
                    "placeholder": "10",
                    "help": "How often to evaluate device load.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_TRIGGER_SEC",
                    "label": "Trigger window (sec)",
                    "placeholder": "30",
                    "help": "How long the thresholds must be exceeded before load reduction activates.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_RECOVER_SEC",
                    "label": "Recover window (sec)",
                    "placeholder": "60",
                    "help": "How long the device must be stable before restarting services.",
                    "sensitive": False
                },
                {
                    "key": "LOAD_REDUCTION_COOLDOWN_SEC",
                    "label": "Stop cooldown (sec)",
                    "placeholder": "30",
                    "help": "Minimum time between stopping additional services.",
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
                "Enable the service to start generating."
            ],
            "enable_key": "ENABLE_HONEYGAIN",
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
            "id": "traffmonetizer",
            "title": "TraffMonetizer",
            "subtitle": "Runs the TraffMonetizer CLI container.",
            "instructions": [
                "Generate a token in your TraffMonetizer dashboard and paste it here."
            ],
            "enable_key": "ENABLE_TRAFFMONETIZER",
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
            "enable_key": "ENABLE_PACKETSTREAM",
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
            "id": "packetshare",
            "title": "PacketShare",
            "subtitle": "Runs the PacketShare client container.",
            "instructions": [
                "Use your PacketShare account email and password.",
                "Enabling this service accepts the PacketShare TOS for the container."
            ],
            "enable_key": "ENABLE_PACKETSHARE",
            "fields": [
                {
                    "key": "PACKETSHARE_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your PacketShare login email.",
                    "sensitive": False
                },
                {
                    "key": "PACKETSHARE_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your PacketShare login password.",
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
            "enable_key": "ENABLE_REPOCKET",
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
            "enable_key": "ENABLE_EARNFM",
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
            "subtitle": "Runs the Grass (GetGrass) container.",
            "instructions": [
                "Use your GetGrass account credentials."
            ],
            "enable_key": "ENABLE_GRASS",
            "fields": [
                {
                    "key": "GRASS_USER",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your GetGrass login email.",
                    "sensitive": False
                },
                {
                    "key": "GRASS_PASS",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your GetGrass login password.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "mysterium",
            "title": "Mysterium",
            "subtitle": "Runs the Mysterium node container.",
            "instructions": [
                "Enable the service to start the node.",
                "Use the Mysterium/MystNodes UI to finish node setup."
            ],
            "enable_key": "ENABLE_MYSTERIUM",
            "fields": []
        },
        {
            "id": "pawns",
            "title": "Pawns",
            "subtitle": "Runs the Pawns client container.",
            "instructions": [
                "Use your Pawns account email and password."
            ],
            "enable_key": "ENABLE_PAWNS",
            "fields": [
                {
                    "key": "PAWNS_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your Pawns login email.",
                    "sensitive": False
                },
                {
                    "key": "PAWNS_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your Pawns login password.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "proxyrack",
            "title": "ProxyRack",
            "subtitle": "Runs the ProxyRack Peer Program container.",
            "instructions": [
                "Paste your ProxyRack device UUID.",
                "Optionally add an API key if you want automatic device association."
            ],
            "enable_key": "ENABLE_PROXYRACK",
            "fields": [
                {
                    "key": "PROXYRACK_UUID",
                    "label": "Device UUID",
                    "placeholder": "",
                    "help": "ProxyRack device UUID.",
                    "sensitive": True
                },
                {
                    "key": "PROXYRACK_API_KEY",
                    "label": "API key",
                    "placeholder": "",
                    "help": "ProxyRack API key (optional).",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "bitping",
            "title": "Bitping",
            "subtitle": "Runs the Bitping node container.",
            "instructions": [
                "Use your Bitping account credentials.",
                "If your account uses MFA, provide the current MFA code (optional).",
                "Avoid running multiple Bitping nodes pointing to the same credentials directory/volume."
            ],
            "enable_key": "ENABLE_BITPING",
            "fields": [
                {
                    "key": "BITPING_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your Bitping login email.",
                    "sensitive": False
                },
                {
                    "key": "BITPING_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your Bitping login password.",
                    "sensitive": True
                },
                {
                    "key": "BITPING_MFA",
                    "label": "MFA code",
                    "placeholder": "",
                    "help": "Current MFA code (leave blank if not enabled).",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "wizardgain",
            "title": "WizardGain",
            "subtitle": "Runs the WizardGain worker container.",
            "instructions": [
                "Use the email address registered with WizardGain.",
                "Enable the service to start generating."
            ],
            "enable_key": "ENABLE_WIZARDGAIN",
            "fields": [
                {
                    "key": "WIZARDGAIN_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your WizardGain login email.",
                    "sensitive": False
                }
            ]
        },
        {
            "id": "wipter",
            "title": "Wipter",
            "subtitle": "Runs the Wipter client.",
            "instructions": [
                "If wipter.service is installed on the host, the native service will be used.",
                "Otherwise, the Docker-based Wipter container from the bundled IGM stack will be used."
            ],
            "enable_key": "ENABLE_WIPTER",
            "fields": [
                {
                    "key": "WIPTER_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Your Wipter login email.",
                    "sensitive": False
                },
                {
                    "key": "WIPTER_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Your Wipter login password.",
                    "sensitive": True
                },
                {
                    "key": "VNC_PASS",
                    "label": "VNC password",
                    "placeholder": "••••••••",
                    "help": "Optional: password for the Wipter VNC UI (if supported by the image).",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "uprock",
            "title": "Uprock",
            "subtitle": "Runs the Uprock client.",
            "instructions": [
                "Install Uprock on the host and register a systemd unit named 'uprock.service'.",
                "Enable the service here to start it automatically."
            ],
            "enable_key": "ENABLE_UPROCK",
            "fields": [
                {
                    "key": "UPROCK_EMAIL",
                    "label": "Email",
                    "placeholder": "you@example.com",
                    "help": "Optional: stored for your reference or for custom installers.",
                    "sensitive": False
                },
                {
                    "key": "UPROCK_PASSWORD",
                    "label": "Password",
                    "placeholder": "••••••••",
                    "help": "Optional: stored for your reference or for custom installers.",
                    "sensitive": True
                }
            ]
        },
        {
            "id": "pingpong",
            "title": "Pingpong",
            "subtitle": "Runs the Pingpong multi-mining client.",
            "instructions": [
                "Log in to Pingpong dashboard and create a device to get your Key.",
                "Paste the Device Key below.",
                "Configure sub-services (depins) below. Saving config will run 'PINGPONG config set ...' and restart the selected depins."
            ],
            "enable_key": "ENABLE_PINGPONG",
            "fields": [
                {
                    "key": "PINGPONG_KEY",
                    "label": "Device Key",
                    "placeholder": "device_key_...",
                    "help": "Your Pingpong Device Key.",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_0G_PRIVATE_KEY",
                    "label": "0G account private key",
                    "placeholder": "0x...",
                    "help": "Used for: PINGPONG config set --0g=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_AIOZ_PRIV_KEY",
                    "label": "AIOZ priv_key",
                    "placeholder": "0x...",
                    "help": "Used for: PINGPONG config set --aioz=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_GRASS_ACCESS",
                    "label": "Grass access token",
                    "placeholder": "access_...",
                    "help": "Used for: PINGPONG config set --grass.access=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_GRASS_REFRESH",
                    "label": "Grass refresh token",
                    "placeholder": "refresh_...",
                    "help": "Used for: PINGPONG config set --grass.refresh=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_BLOCKMESH_EMAIL",
                    "label": "BlockMesh email",
                    "placeholder": "you@example.com",
                    "help": "Used for: PINGPONG config set --blockmesh.email=***",
                    "sensitive": False
                },
                {
                    "key": "PINGPONG_BLOCKMESH_PASSWORD",
                    "label": "BlockMesh password",
                    "placeholder": "••••••••",
                    "help": "Used for: PINGPONG config set --blockmesh.pwd=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_DAWN_EMAIL",
                    "label": "DAWN email",
                    "placeholder": "you@example.com",
                    "help": "Used for: PINGPONG config set --dawn.email=***",
                    "sensitive": False
                },
                {
                    "key": "PINGPONG_DAWN_PASSWORD",
                    "label": "DAWN password",
                    "placeholder": "••••••••",
                    "help": "Used for: PINGPONG config set --dawn.pwd=***",
                    "sensitive": True
                },
                {
                    "key": "PINGPONG_HEMI_KEY",
                    "label": "Hemi key",
                    "placeholder": "hemi_...",
                    "help": "Used for: PINGPONG config set --hemi=***",
                    "sensitive": True
                }
            ]
        }
    ]
