"""
Object storage service — wraps Emergent Object Storage API.
Init once at startup, reuse storage_key globally.
"""
import logging
import os
import uuid
import requests

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "budezivo"

_storage_key: str | None = None

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp", "image/gif"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_PROGRAM_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def init_storage() -> str:
    """Call once at startup. Returns a reusable storage_key."""
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": EMERGENT_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    logger.info("Object storage initialized")
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file. Returns {"path": ..., "size": ...}."""
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    """Download file. Returns (content_bytes, content_type)."""
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def upload_logo(institution_id: str, file_data: bytes, content_type: str, extension: str) -> str:
    """Upload a logo and return the storage path."""
    file_id = uuid.uuid4()
    path = f"{APP_NAME}/logos/{institution_id}/{file_id}.{extension}"
    put_object(path, file_data, content_type)
    return path


def upload_program_image(institution_id: str, program_id: str, file_data: bytes, content_type: str, extension: str) -> str:
    """Upload a program cover image and return the storage path."""
    file_id = uuid.uuid4()
    path = f"{APP_NAME}/programs/{institution_id}/{program_id}/{file_id}.{extension}"
    put_object(path, file_data, content_type)
    return path
