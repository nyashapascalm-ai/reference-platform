import pgserver, tempfile, re, os, json

pg = pgserver.get_server(tempfile.mkdtemp())
uri = pg.get_uri()

def assert_clean(out, label):
    if "ERROR" in out:
        print(f"!! {label}:\n{out}"); raise SystemExit(1)
    print(f"OK  {label}")

# stub Supabase-provided bits + apply the real migration
assert_clean(pg.psql("""
create schema if not exists auth;
create table auth.users (id uuid primary key);
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('app.uid', true), '')::uuid $$;
create domain citext as text;
"""), "stub auth + citext")
raw = open("../supabase/migrations/0001_core_schema.sql").read()
assert_clean(pg.psql(re.sub(r'(?im)^create extension .*$','-- ext',raw)), "apply core schema")

CO = "11111111-1111-1111-1111-111111111111"   # council org
TMPL = "cccccccc-1111-1111-1111-111111111111" # statutory template
assert_clean(pg.psql(f"""
insert into orgs (id,name,org_type,vertical,email_domain)
 values ('{CO}','Barchester County Council','local_authority','social_work','barchester.gov.uk');
insert into reference_templates (id,vertical,name,version,field_schema)
 values ('{TMPL}','social_work','Practice-based reference (statutory)','2024.10',
         '{{"required":["dates","role","conduct","competence","safeguarding"]}}');
"""), "seed org + template")

# point the app at this throwaway DB and drive it via the real ASGI app
os.environ["DATABASE_URL"] = uri
from fastapi.testclient import TestClient
from app.main import app
from app.hashing import content_hash

results = []
def check(name, cond):
    results.append(cond); print(("OK  " if cond else "!!  ")+name)

with TestClient(app) as cx:
    check("health", cx.get("/health").json().get("ok") is True)

    # 1. verify a worker (SWE stubbed -> verified)
    r = cx.post("/workers/verify", json={
        "full_name":"Sam Okafor","vertical":"social_work",
        "registration_body":"swe","registration_number":"SW123456",
        "dbs_certificate_number":"001234567890"})
    wid = r.json()["worker_id"]
    check("worker verified", r.status_code==201 and r.json()["registration_status"]=="verified")

    # 2. council drafts a reference WITH a domain-matching referee
    good = {"dates":"2022-2024","role":"Senior Practitioner","conduct":"no concerns",
            "competence":"strong","safeguarding":"none"}
    r = cx.post("/references", headers={"X-Org-Id":CO}, json={
        "worker_id":wid,"template_id":TMPL,"assignment_context":"Children & Families",
        "content":good,
        "referee":{"full_name":"Dana Hollis","job_title":"Team Manager","work_email":"dana@barchester.gov.uk"}})
    rid = r.json()["reference_id"]
    check("reference drafted", r.status_code==201 and r.json()["status"]=="draft")
    check("referee domain verified", r.json()["referee"]["domain_verified"] is True)

    # 3. publish -> server computes the tamper-evident hash
    r = cx.post(f"/references/{rid}/publish", headers={"X-Org-Id":CO})
    expect = content_hash(wid, CO, good)
    check("published with correct server-side hash",
          r.status_code==200 and r.json()["content_hash"]==expect)

    # 3b. NEGATIVE: a reference missing a required field cannot publish
    bad = dict(good); bad.pop("safeguarding")
    r2 = cx.post("/references", headers={"X-Org-Id":CO},
                 json={"worker_id":wid,"template_id":TMPL,"content":bad})
    bad_id = r2.json()["reference_id"]
    r2p = cx.post(f"/references/{bad_id}/publish", headers={"X-Org-Id":CO})
    check("publish blocked when required field missing (422)", r2p.status_code==422)

    # 4. worker mints the £5 consent link (raw token returned once)
    r = cx.post("/grants", headers={"X-Worker-Id":wid},
                json={"reference_id":rid,"granted_to_email":"priya@swlocums.co.uk","expires_in_days":14})
    token = r.json()["share_token"]
    check("grant minted, raw token returned", r.status_code==201 and len(token) > 20)

    # 4b. NEGATIVE: a different worker cannot share this reference
    other = "aaaaaaaa-9999-9999-9999-999999999999"
    rno = cx.post("/grants", headers={"X-Worker-Id":other}, json={"reference_id":rid})
    check("non-owner worker cannot share (403)", rno.status_code==403)

    # 5. grantee redeems the link -> gets the source record, access logged
    r = cx.get(f"/share/{token}", headers={"X-Email":"priya@swlocums.co.uk"})
    body = r.json()
    check("share redeemed, content delivered", r.status_code==200 and body["content"]==good)
    check("share carries verifiable hash", body["content_hash"]==expect)

    # 5b. NEGATIVE: a bad token is rejected
    check("invalid token rejected (404)", cx.get("/share/not-a-real-token").status_code==404)

    # 6. worker revokes consent -> link dies
    pg.psql(f"update access_grants set status='revoked',revoked_at=now() where reference_id='{rid}';")
    check("revoked link refused (403)", cx.get(f"/share/{token}").status_code==403)

    # 7. the read was audited
    n = pg.psql(f"select count(*)::int from access_log where reference_id='{rid}';")
    logged = [l.strip() for l in n.splitlines() if l.strip().isdigit()]
    check("access logged in audit trail", logged and int(logged[-1])>=1)

print("\n==> ALL CHECKS PASSED" if all(results) else "\n==> CHECK FAILURE")
pg.cleanup()
raise SystemExit(0 if all(results) else 1)
