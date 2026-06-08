"""Firebase Admin SDK initialisation. Reads service account from
backend/.env as a base64-encoded JSON string (FIREBASE_SERVICE_ACCOUNT_B64)
to keep the JSON out of the source tree.
"""
import base64
import json
import os
from threading import Lock

import firebase_admin
from firebase_admin import credentials, firestore, storage

_lock = Lock()
_initialised = False


def _init_app() -> None:
    global _initialised
    with _lock:
        if _initialised:
            return
        b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64")
        if not b64:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_B64 is not set in backend/.env"
            )
        sa = json.loads(base64.b64decode(b64))
        bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
        if not bucket:
            raise RuntimeError(
                "FIREBASE_STORAGE_BUCKET is not set in backend/.env"
            )
        cred = credentials.Certificate(sa)
        try:
            firebase_admin.initialize_app(cred, {"storageBucket": bucket})
        except ValueError:
            # Already initialised by another worker
            pass
        _initialised = True


def get_firestore():
    _init_app()
    return firestore.client()


def get_bucket():
    _init_app()
    return storage.bucket()
