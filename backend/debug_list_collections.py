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

print("ALL top-level collections in project pnc-induction-portal (default DB):")
cols = list(db.collections())
if not cols:
    print("   (none — the Firestore database has no collections yet)")
for c in cols:
    n = sum(1 for _ in c.list_documents())
    print(f"   - {c.id}   ({n} docs)")
