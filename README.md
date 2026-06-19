# Reference Custody Platform

Verified, consent-gated employment references for regulated UK sectors.
Built core-once, reskinned per regulator (social work → healthcare → teaching).

Stack: **Supabase** (Postgres + auth + RLS) · **FastAPI on Railway** (verification, AI, hashing) · **Next.js on Vercel** (org dashboards, worker portal, share flow).

---

## Status

| Step | What | State |
|------|------|-------|
| 1 | Core data model — identity spine, custody ledger, consent gate, audit, multi-tenant RLS | **✅ verified** |
| 2 | FastAPI backend — worker verification, reference publish+hash, mint/redeem grant | next |
| 3 | Next.js — council/agency dashboards, worker portal, £5 share link | — |
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
