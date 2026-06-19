import pgserver, tempfile, re, hashlib, secrets, json

d = tempfile.mkdtemp()
pg = pgserver.get_server(d)

def scalar(sql):
    for line in pg.psql(sql).splitlines():
        s = line.strip()
        if s.isdigit():
            return s
    return None

def assert_clean(out, label):
    if "ERROR" in out:
        print(f"!! {label} produced errors:\n{out}")
        raise SystemExit(1)
    print(f"OK  {label}")

assert_clean(pg.psql("""
create schema if not exists auth;
create table auth.users (id uuid primary key);
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('app.uid', true), '')::uuid
$$;
create domain citext as text;
"""), "stub auth + citext")

raw = open("supabase/migrations/0001_core_schema.sql").read()
local = re.sub(r'(?im)^create extension .*$', '-- (extension provided by platform)', raw)
assert_clean(pg.psql(local), "apply 0001_core_schema.sql")

CO_COUNCIL = "11111111-1111-1111-1111-111111111111"
CO_AGENCY  = "22222222-2222-2222-2222-222222222222"
U_COUNCIL  = "aaaaaaaa-1111-1111-1111-111111111111"
U_AGENCY   = "aaaaaaaa-2222-2222-2222-222222222222"
U_WORKER   = "aaaaaaaa-3333-3333-3333-333333333333"
W1 = "bbbbbbbb-1111-1111-1111-111111111111"
T1 = "cccccccc-1111-1111-1111-111111111111"
R1 = "dddddddd-1111-1111-1111-111111111111"

assert_clean(pg.psql(f"""
insert into auth.users (id) values ('{U_COUNCIL}'),('{U_AGENCY}'),('{U_WORKER}');
insert into orgs (id,name,org_type,vertical,email_domain) values
 ('{CO_COUNCIL}','Barchester County Council','local_authority','social_work','barchester.gov.uk'),
 ('{CO_AGENCY}','SW Locums Ltd','agency','social_work','swlocums.co.uk');
insert into profiles (id,org_id,role,full_name,email) values
 ('{U_COUNCIL}','{CO_COUNCIL}','org_admin','Dana Hollis','dana@barchester.gov.uk'),
 ('{U_AGENCY}','{CO_AGENCY}','hiring_manager','Priya Shah','priya@swlocums.co.uk'),
 ('{U_WORKER}',null,'worker','Sam Okafor','sam@example.com');
insert into workers (id,profile_id,full_name,vertical,registration_body,registration_number,registration_status)
 values ('{W1}','{U_WORKER}','Sam Okafor','social_work','swe','SW123456','verified');
insert into reference_templates (id,vertical,name,version,field_schema) values
 ('{T1}','social_work','Practice-based reference (statutory)','2024.10',
  '{{"required":["dates","role","conduct","competence","safeguarding"]}}');
"""), "seed orgs / worker / template")

payload = {"dates":"2022-2024","role":"Senior Practitioner","conduct":"no concerns",
           "competence":"strong","safeguarding":"none"}
canon = json.dumps(payload, sort_keys=True, separators=(',',':'))
chash = hashlib.sha256(f"{W1}|barchester|{canon}".encode()).hexdigest()

assert_clean(pg.psql(f"""
insert into "references" (id,worker_id,issuing_org_id,template_id,status,content,assignment_context)
 values ('{R1}','{W1}','{CO_COUNCIL}','{T1}','draft','{json.dumps(payload)}'::jsonb,'Children & Families team');
insert into referees (reference_id,full_name,job_title,work_email,email_domain,domain_verified,auth_method)
 values ('{R1}','Dana Hollis','Team Manager','dana@barchester.gov.uk','barchester.gov.uk',true,'email_link');
update "references" set status='published',content_hash='{chash}',published_at=now() where id='{R1}';
"""), "publish reference")
print("    content_hash:", chash[:16], "...")

before = scalar('select count(*)::int from "references";')
pg.psql(f"""insert into "references" (worker_id,issuing_org_id,template_id,status,content)
  values ('{W1}','{CO_COUNCIL}','{T1}','published','{{}}');""")
after = scalar('select count(*)::int from "references";')
print("OK  constraint blocks publish-without-hash (row rejected)" if before==after
      else "!! constraint did NOT fire")

raw_token = secrets.token_urlsafe(24)
tok_hash = hashlib.sha256(raw_token.encode()).hexdigest()
assert_clean(pg.psql(f"""
insert into access_grants (worker_id,reference_id,token_hash,granted_to_email,granted_to_org_id,expires_at)
 values ('{W1}','{R1}','{tok_hash}','priya@swlocums.co.uk','{CO_AGENCY}', now() + interval '14 days');
"""), "mint consent grant (raw token -> sha256 only)")

pg.psql("""
create role app_user nologin;
grant usage on schema public, auth to app_user;
grant select, insert, update on all tables in schema public to app_user;
grant execute on all functions in schema public to app_user;
grant execute on function auth.uid() to app_user;
""")

def refs_visible_to(uid):
    return scalar(f"""
      set session authorization app_user;
      select set_config('app.uid','{uid}', false);
      select count(*)::int from "references";
    """)

council = refs_visible_to(U_COUNCIL)
agency  = refs_visible_to(U_AGENCY)
worker  = refs_visible_to(U_WORKER)
print(f"RLS  council/issuer sees {council} | agency/grantee sees {agency} | worker/owner sees {worker}")

pg.psql(f"update access_grants set status='revoked',revoked_at=now() where reference_id='{R1}';")
agency_after = refs_visible_to(U_AGENCY)
print(f"RLS  after worker revokes consent: agency/grantee sees {agency_after}")

ok = council=='1' and agency=='1' and worker=='1' and agency_after=='0'
print("\n==> ALL CHECKS PASSED" if ok else "\n==> CHECK FAILURE")
pg.cleanup()
raise SystemExit(0 if ok else 1)
