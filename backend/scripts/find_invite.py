"""Investigation: where did invite PNC-V7WU-J37Z go?"""
import base64, json, os, sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv("/app/backend/.env")
sa = json.loads(base64.b64decode(os.environ["FIREBASE_SERVICE_ACCOUNT_B64"]))
cred = credentials.Certificate(sa)
firebase_admin.initialize_app(cred)
db = firestore.client()
print(f"Project: {sa['project_id']}")
print(f"Service account: {sa['client_email']}")
print("=" * 80)

TARGET_EMAIL = "lupanciucvaleria10@gmail.com"
TARGET_CODES = ["PNC-V7WU-J37Z", "pnc-v7wu-j37z", "V7WUJ37Z", "PNCV7WUJ37Z"]

print("\n[A] Exact-code search across access_codes:")
for code in TARGET_CODES:
    q = db.collection("access_codes").where(filter=FieldFilter("code", "==", code))
    found = list(q.stream())
    print(f"   code='{code}' -> {len(found)} hit(s)")
    for d in found:
        print(f"     id={d.id}  data={d.to_dict()}")

print("\n[B] All access_codes for email lupanciucvaleria10@gmail.com:")
q = db.collection("access_codes").where(filter=FieldFilter("email", "==", TARGET_EMAIL.lower()))
hits = list(q.stream())
print(f"   {len(hits)} hit(s)")
for d in hits:
    print(f"     id={d.id}  data={d.to_dict()}")

print("\n[C] Last 10 invites overall (sorted by invited_at desc, manual sort):")
all_rows = []
for d in db.collection("access_codes").stream():
    rec = d.to_dict() or {}
    rec["_id"] = d.id
    all_rows.append(rec)
all_rows.sort(key=lambda r: r.get("invited_at") or r.get("created_at") or "", reverse=True)
for r in all_rows[:15]:
    print(f"   {r.get('invited_at') or r.get('created_at') or '?':<32} "
          f"code={r.get('code')!r:<22} "
          f"email={r.get('email')!r:<40} "
          f"status={r.get('invite_status')!r} used={r.get('used')}")
print(f"   TOTAL access_codes in Firestore: {len(all_rows)}")
