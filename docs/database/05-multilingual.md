# 05 — Multilingual Strategy

## Requirements mapped

| Requirement | Mechanism |
| ----------- | --------- |
| Original language | `schemes.original_language` + `scheme_regional_languages.is_original` |
| Translated content | `localized_texts` EAV rows with `is_machine_translated`, `translation_status` |
| Language codes | `languages.code` (BCP-47 subset, matches `shared` SUPPORTED_LANGUAGES) |
| Fallback language | `languages.is_fallback` (exactly one: `en`) |
| Future language additions | add row to `languages` + `scheme_regional_languages` + translation job — no schema change |

## The three cooperating structures

### 1. `languages` — capability catalog
`code`, `name`, `native_name`, `script`, `is_rtl`, capability flags (`stt`,
`tts`, `indic_trans`), `is_fallback`, `active`. Mirrors
`SUPPORTED_LANGUAGES` in `shared/src/domain/language.ts`; the seed imports the
same data. Adding a language = one row + IndicTrans2 config.

### 2. `scheme_regional_languages` — per-scheme language coverage
Which languages each scheme is *available* in, plus translation state:
`is_original` (native source), `translation_status`
(`not_translated → pending → machine_translated → human_reviewed`), `verified`,
`last_translated_at`. Central schemes default to all active languages;
state schemes ship the state's languages.

### 3. `localized_texts` — the translation store (EAV)

| Column | Purpose |
| ------ | ------- |
| entity_type | `scheme`, `category`, `faq`, `step`, `benefit`, `document`, `link`, `centre`, `filter`, `notification` |
| entity_id | row PK of that entity |
| field | localizable field (`name`, `short_name`, `description`, `summary`, `benefit_text`, `question`, `answer`, `title`, …) |
| language | `languages.code` |
| value | the translated text |
| is_machine_translated | provenance flag |
| translation_status | `canonical \| machine \| reviewed` |
| source_language | what `en`-or-original it was translated from |

**PK** `(entity_type, entity_id, field, language)` — one canonical row per
field/language, idempotent upserts from the translation pipeline.

### How a scheme looks in Tamil
```
SELECT lv.value
FROM schemes s
JOIN scheme_regional_languages srl ON srl.scheme_id = s.id AND srl.language_code='ta'
JOIN localized_texts lv
  ON lv.entity_type='scheme' AND lv.entity_id=s.id AND lv.field='name' AND lv.language='ta'
WHERE s.code='PM-KISAN';
```

## Canonical English + fallback

- `schemes.name_en / description_en / summary_en` are the **canonical snapshot**
  (RAG grounding + search + scoring). `original_language` tells which language is
  the true source; when it is not English, the English columns hold the canonical
  translation and `scheme_regional_languages` marks `is_original`.
- When a requested language has no `localized_texts` row, the resolver falls back
  to `languages.is_fallback = 'en'`, then to `name_native`. Fallback chain:
  requested → English → native → stripped text. This satisfies
  "fallback language" and keeps UIs functional before translation completes.

## Translation pipeline (data layer contract)

1. New/updated scheme content → `content_hash` changes → job enqueues
   `(scheme_id, target_languages)`.
2. Worker (IndicTrans2 primary, Google fallback) writes `localized_texts` with
   `is_machine_translated=true`, `translation_status='machine'`.
3. `scheme_regional_languages` status flips `pending → machine_translated`.
4. Optional human review flips `human_reviewed` + `verified`.
5. Results are cached in `translations_cache` (Redis, PG fallback) keyed by
   `(text_hash, language)`.

## Search across languages

Doc 06 covers it: per-language `tsvector` (to_tsvector with Indic dicts),
pg_trgm fuzzy matching on both English and Indic script text, and (future)
multilingual embeddings. `localized_texts.value` gets a trigram GIN index with
`language` filtering so regional-language search hits translated content.

## Chat contract alignment

`chat_messages.content` (canonical) + `rendered_text` (user's language) map to
the shared `ChatMessage` fields — the DB multilingual design already supports
switching a conversation's language without re-calling the LLM.
