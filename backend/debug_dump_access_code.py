import os, json, base64
from pathlib import Path

env_path = Path("/app/backend/.env")
for line in env_path.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

sa = json.loads(base64.b64decode(os.environ["FIREBASE_SERVICE_ACCOUNT_B64"]))
import firebase_admin
from firebase_admin import credentials, firestore
try: firebase_admin.initialize_app(credentials.Certificate(sa))
except ValueError: pass
db = firestore.client()

print("--- Docs in `access_code` (singular) ---")
for d in db.collection("access_code").stream():
    print("Document ID:", d.id)
    for k, v in d.to_dict().items():
        print(f"   {k} = {v!r}   (type={type(v).__name__})")
    print()
