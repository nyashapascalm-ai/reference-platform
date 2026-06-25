"""Supabase Storage helper (service-key, server-side only).

Uploads to and signs download URLs for private buckets via the Storage REST API.
Never expose the service key to the browser.
"""
import os
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def configured() -> bool:
    return bool(SUPABASE_URL and SERVICE_KEY)


async def upload(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload bytes to bucket/key. Overwrites if exists (upsert)."""
    if not configured():
        raise RuntimeError("Supabase Storage is not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY).")
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{key}"
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, content=data)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed ({r.status_code}): {r.text[:200]}")
    return True


async def signed_url(bucket: str, key: str, expires_in: int = 300) -> str:
    """Return a short-lived signed download URL for a private object."""
    if not configured():
        raise RuntimeError("Supabase Storage is not configured.")
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{key}"
    headers = {"Authorization": f"Bearer {SERVICE_KEY}", "apikey": SERVICE_KEY,
               "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json={"expiresIn": expires_in})
        if r.status_code != 200:
            raise RuntimeError(f"Sign URL failed ({r.status_code}): {r.text[:200]}")
        path = r.json().get("signedURL") or r.json().get("signedUrl")
    return f"{SUPABASE_URL}/storage/v1{path}"
