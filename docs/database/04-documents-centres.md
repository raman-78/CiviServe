# 04 — Documents & Service Centres

## Document system (per-scheme requirements → citizen files)

Three layers keep the system normalized and future-ready for OCR:

```
document_types (master catalog)      ← what a document IS
   │
scheme_documents (per-scheme need)   ← what a scheme REQUIRES
   │
user_documents (citizen's files)     ← what the USER PROVIDED (future OCR)
```

### `document_types` — master catalogue
Canonical kinds with their capabilities stored once: `code` (`AADHAAR`, `PAN`,
`RATION_CARD`, `INCOME_CERT`, `DISABILITY_CERT`, …), `category`
(identity/address/income/age/caste/bank/land/disability/family/photo/other),
`ocr_supported`, default `accepted_formats`. New document kind = seed row.

### `scheme_documents` — requirement per scheme
Covers every requirement in the brief:

| Requirement | Column |
| ----------- | ------ |
| Required documents | `is_required = true` |
| Optional documents | `is_required = false` |
| Document descriptions | `description_en` (+ `localized_texts` for other languages) |
| Accepted file formats | `accepted_file_formats varchar[]` (pdf/jpg/png/jpeg/…) |
| Validity period | `validity_period_days int` (e.g. income certificate ≈ 90 days) |
| Verification status / level | `verification_required bool` + `verification_status` on `user_documents` |
| OCR support | `ocr_supported bool` (mirrors catalog; overridable per scheme) |
| Ordering | `sort_order` |

`custom_name_en` + nullable `document_type_id` allow schemes to demand a specific
official certificate not in the catalog without blocking.

### `user_documents` — the citizen's file (future OCR / voice / mobile)
Captures upload state end-to-end: `file_ref` (object-store key),
`file_format`, `ocr_text` (Tesseract/PaddleOCR output), `verification_status`
(`not_submitted → pending → verified | rejected | expired`), `reviewed_by`
(admin), `expires_at` (derived from `validity_period_days`). This is the row
that makes "document verification" a real product feature and the doc-based
eligibility filter (`source_field = document_types.code`) work.

### Document → eligibility coupling
A rule such as *"must have a valid disability certificate"* is expressed as an
`eligibility_rules` row with `filter_key` pointing at a `document_types.code`;
the engine evaluates it against `user_documents` (status + expiry). OCR flow
(once implemented) writes `ocr_text` + suggests `verification_status` changes.

---

## Service centres (CSC / e-Sevai / MeeSeva / Jan Seva / district offices)

### `service_centres`
One table, typed, covering every centre category in the brief:

| Requirement | Column(s) |
| ----------- | --------- |
| CSC / e-Sevai / MeeSeva / Jan Seva / District offices / banks / post offices | `centre_type` CK `csc\|e-sevai\|meeseva\|jan-seva\|district-office\|post_office\|bank\|seva-kendra` |
| Address | `address`, `district`, `state_code` (FK) |
| Latitude / Longitude | `lat`/`lng` (double, WGS84) + derived `geom GEOGRAPHY(Point,4326)` |
| Working hours | `working_hours jsonb` `{"mon":{"open":"09:00","close":"17:00"}}` |
| Contact number | `contact_number`, `email`, `website` |
| Available services | M2M → `service_centre_services` (`scheme_application`, `pan`, `passport`, `g2c`, `document_fetch`, …) |
| Trust/recency | `verified bool`, `source` (`manual\|import\|api`), `active` |

### Nearby queries ("locate nearest CSC")
```
SELECT * FROM service_centres
WHERE ST_DWithin(geom, ST_MakePoint($lng,$lat)::geography, $radius_m)
ORDER BY geom <-> ST_MakePoint($lng,$lat)::geography
LIMIT 20;
```
Backed by the **GiST index** on `geom`. `distanceKm` is returned to the client to
match `ServiceCenter` in `shared/src/domain/centers.ts`.

### Ingestion & freshness
- Bulk import via `database/scripts` + `seeds/centers` (CSV, geocoded).
- `source = 'api'` supports scheduled sync from public CSC/e-Sevai datasets.
- `verified` flag gates showing a centre in "trusted" mode; unverified entries
  still appear but are flagged in the UI.

## Multilingual centres
Names, addresses, and services are localizable through the shared
`localized_texts` mechanism (`entity_type='centre'`, `entity_type='centre_service'`),
with the English column as canonical snapshot (doc 05).
