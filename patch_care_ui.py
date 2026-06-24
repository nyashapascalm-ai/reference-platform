"""
Patch frontend/app/dashboard/page.js for the care sector. Run from repo root:

    python patch_care_ui.py

Edits:
  1. OrgPanel loads ALL active templates (not just social_work).
  2. Reference form renders fields from template.field_schema.fields
     (labels + textareas), falling back to required-only rendering.
  3. RegisterWorker: "Not on a professional register" option (registration_body
     'none', also sets vertical 'care'); hides the number field when chosen.
  4. Result screen no longer hard-codes "SWE register"; adds the
     not_applicable (identity-based) case. ASCII-only matches.

Idempotent: skips edits already applied.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "dashboard", "page.js")

edits = [
    # 1) load all templates instead of only social_work
    (
        "      const t = await api('/templates?vertical=social_work', { auth: false });",
        "      const t = await api('/templates', { auth: false });",
    ),

    # 2) template-driven field rendering (labels + textareas)
    (
        "      {required.map((field) => (\n"
        "        <div key={field}>\n"
        "          <label>{field}</label>\n"
        "          <input value={content[field] || ''} onChange={upc(field)} />\n"
        "        </div>\n"
        "      ))}",

        "      {(tpl?.field_schema?.fields && tpl.field_schema.fields.length\n"
        "        ? tpl.field_schema.fields\n"
        "        : required.map((k) => ({ key: k, label: k, type: 'text' }))\n"
        "      ).map((fld) => (\n"
        "        <div key={fld.key}>\n"
        "          <label>{fld.label}{required.includes(fld.key) ? ' *' : ''}</label>\n"
        "          {fld.type === 'textarea'\n"
        "            ? <textarea rows={3} value={content[fld.key] || ''} onChange={upc(fld.key)} />\n"
        "            : <input value={content[fld.key] || ''} onChange={upc(fld.key)} />}\n"
        "        </div>\n"
        "      ))}",
    ),

    # 3) RegisterWorker: add no-register option + hide number field
    (
        "      <label>Registration body</label>\n"
        "      <select value={f.registration_body} onChange={up('registration_body')}>\n"
        '        <option value="swe">Social Work England (SWE)</option>\n'
        '        <option value="nmc">NMC</option><option value="gmc">GMC</option>\n'
        '        <option value="hcpc">HCPC</option><option value="trn">TRN</option>\n'
        "      </select>\n"
        "      <label>Registration number</label><input value={f.registration_number} onChange={up('registration_number')} placeholder=\"SW123456\" />",

        "      <label>Registration body</label>\n"
        "      <select value={f.registration_body} onChange={(e) => setF({ ...f, registration_body: e.target.value, vertical: e.target.value === 'none' ? 'care' : f.vertical })}>\n"
        '        <option value="swe">Social Work England (SWE)</option>\n'
        '        <option value="nmc">NMC</option><option value="gmc">GMC</option>\n'
        '        <option value="hcpc">HCPC</option><option value="trn">TRN</option>\n'
        '        <option value="none">Not on a professional register (e.g. care worker)</option>\n'
        "      </select>\n"
        "      {f.registration_body !== 'none'\n"
        "        ? (<><label>Registration number</label><input value={f.registration_number} onChange={up('registration_number')} placeholder=\"SW123456\" /></>)\n"
        "        : (<div className=\"kv\" style={{ margin: '6px 0' }}>No register number needed. Identity is bound to the DBS number (if given) and confirmed by the referee.</div>)}",
    ),

    # 4a) result screen: 'Verified on the SWE register' -> 'Verified on the register' (ASCII-only, leaves the tick intact)
    (
        "Verified on the SWE register",
        "Verified on the register",
    ),

    # 4b) result screen: add not_applicable branch (ASCII-only, leaves the em-dash 'Pending' string intact)
    (
        "st === 'failed' ? 'Not found on the SWE register' : ",
        "st === 'failed' ? 'Not found on the register' : st === 'not_applicable' ? 'Identity-based (no professional register for this role)' : ",
    ),
]

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

applied = 0
for i, (old, new) in enumerate(edits, 1):
    if new in src and old not in src:
        print(f"  edit {i}: already applied, skipping")
        continue
    n = src.count(old)
    if n != 1:
        print(f"ERROR edit {i}: expected target exactly once, found {n}. No changes written.")
        print("Paste this output back and we'll adjust the match string.")
        sys.exit(1)
    src = src.replace(old, new)
    applied += 1
    print(f"  edit {i}: applied")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print(f"Done. {applied} edit(s) written to {PATH}.")
