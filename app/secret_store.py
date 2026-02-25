import base64
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


@dataclass(frozen=True)
class SecretStorePaths:
    secret_dir: str
    key_path: str


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_secret_dir() -> str:
    override = os.environ.get("MONEYTREE_SECRET_DIR", "").strip()
    if override:
        return override
    if os.name == "posix":
        return "/etc/moneytree"
    return os.path.join(_project_root(), ".secrets")


def secret_paths() -> SecretStorePaths:
    secret_dir = _default_secret_dir()
    return SecretStorePaths(
        secret_dir=secret_dir,
        key_path=os.path.join(secret_dir, "master.key"),
    )


def _ensure_secret_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    if os.name == "posix":
        os.chmod(path, 0o700)


def load_or_create_master_key() -> bytes:
    paths = secret_paths()
    _ensure_secret_dir(paths.secret_dir)

    if os.path.exists(paths.key_path):
        key = open(paths.key_path, "rb").read().strip()
        base64.urlsafe_b64decode(key)
        return key

    key = Fernet.generate_key()
    open(paths.key_path, "wb").write(key + b"\n")
    if os.name == "posix":
        os.chmod(paths.key_path, 0o600)
    return key


def encrypt(plaintext: bytes) -> bytes:
    key = load_or_create_master_key()
    return Fernet(key).encrypt(plaintext)


def decrypt(token: bytes) -> bytes:
    key = load_or_create_master_key()
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Invalid encryption token or wrong key") from exc
