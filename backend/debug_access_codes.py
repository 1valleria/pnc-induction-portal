"""
Read every doc in `access_codes` and print exactly what's there.
Used for debugging the gate validation.
"""
import os, json, base64, sys
from pathlib import Path

# Load .env manually (avoid extra deps)
env_path = Path("/app/backend/.env")
for line in env_path.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64")
if not b64:
    print("ERROR: FIREBASE_SERVICE_ACCOUNT_B64 missing in backend/.env")
    sys.exit(1)

sa = json.loads(base64.b64decode(b64))

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate(sa)
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()

print("=" * 70)
print(f"Project ID from service account: {sa.get('project_id')}")
print("=" * 70)

print("\n--- All documents in `access_codes` collection ---")
docs = list(db.collection("access_codes").stream())
print(f"Total docs found: {len(docs)}\n")

for d in docs:
    data = d.to_dict()
    print(f"Document ID: {d.id}")
    for k, v in data.items():
        # show repr to expose hidden whitespace / case
        print(f"   {k} = {v!r}   (type={type(v).__name__})")
    print()

if not docs:
    print("⚠ The collection is EMPTY (or it does not exist yet).")
    print("  The app's query `where('code','==',<your code>)` will always return zero docs.")
