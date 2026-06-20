# Reference Custody Platform

Verified, consent-gated employment references for regulated UK sectors.
Built core-once, reskinned per regulator (social work → healthcare → teaching).

Stack: **Supabase** (Postgres + auth + RLS) · **FastAPI on Railway** (verification, AI, hashing) · **Next.js on Vercel** (org dashboards, worker portal, share flow).

---

## Status

| Step | What | State |
|------|------|-------|
| 1 | Core data model — identity spine, custody ledger, consent gate, audit, multi-tenant RLS | **✅ verified · live** |
| 2 | FastAPI backend — worker verify, reference publish+hash, mint/redeem grant | **✅ verified** |
| 3 | Next.js — council/agency dashboards, worker portal, £5 share link | next |
| 4 | AI core — drafting, fairness guard, synthesiser, contradiction, collusion | — |
| 5 | Social-work vertical module — SWE check, statutory template, Ofsted dashboard | — |

## Step 1 — what's proven

`supabase/migrations/0001_core_schema.sql` applies cleanly and enforces, at the database level:

- **Identity spine** — every reference/grant binds to a verified `workers` row (SWE/NMC/GMC/HCPC/TRN + DBS + RTW).
- **Custody ledger** — a reference cannot reach `published` without a `content_hash` (tamper-evidence). Enforced by check constraint.
- **Consent gate** — the worker owns their `access_grants`; the raw share token is never stored (sha256 only). Revoking a grant immediately removes the grantee's read access. Proven by RLS test: grantee sees `1` → worker revokes → grantee sees `0`.
- **Tenant isolation** — issuing org sees its own references; granted org sees only what it holds an active grant for; worker sees only their own.

### Run the verification

```bash
pip install pgserver --break-system-packages
python3 verify_schema.py        # spins a throwaway Postgres, applies + tests, exits non-zero on failure
```

The harness stubs the two things Supabase provides in production (the `auth` schema and the `citext` extension); the migration itself is unmodified and production-ready.

### Apply to Supabase

```bash
supabase db push                # or paste 0001_core_schema.sql into the SQL editor
```
`pgcrypto` and `citext` are available by default on Supabase — no action needed.

## Step 2 — backend (verified)

FastAPI in `backend/`. Endpoints, all enforced server-side:

- `POST /workers/verify` — register + verify a worker (SWE check stubbed in `app/swe.py`).
- `POST /references` — issuing org drafts a reference; a domain-matching referee is marked `domain_verified`.
- `POST /references/{id}/publish` — validates the content against the template's required fields, then writes a **server-computed** `content_hash`. A reference cannot publish with missing fields.
- `POST /grants` — the worker mints the £5 consent link; the raw token is returned **once**, only its sha256 is stored. A worker can only share references about themselves.
- `GET /share/{token}` — redeems the link: returns the source record, writes an `access_log` row. Revoked or expired links are refused.

Dev auth uses `X-Org-Id` / `X-Worker-Id` headers as a stand-in for the verified Supabase JWT (to be wired in a later step).

### Run locally
```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="<your Supabase connection-pooler URI>"
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```

### Verify (Linux/Mac only — pgserver has no Windows build)
```bash
pip install pgserver fastapi asyncpg httpx uvicorn
python verify_backend.py   # 17 checks incl. negative cases; already passing
```
