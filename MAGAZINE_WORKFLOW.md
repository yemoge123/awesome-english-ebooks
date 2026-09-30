# Magazine Translation Workflow

> Canonical strategy: `MAGAZINE_TRANSLATION_STRATEGY.md` (vNext.3). If this workflow document conflicts with the strategy on publication scope, selection, queue semantics, QA layers, package shape, runtime authority, or long-term execution, the strategy wins.

## Scope

This workflow covers personal magazine translation from authorized EPUB sources through mobile reading output.

It is independent from RSS delivery. Do not restore RSS push as part of this workflow unless the user explicitly asks for it.

## Canonical flow

```text
Authorized EPUB
→ extract article metadata + semantic source blocks + image mapping
→ select articles into selection.json
→ create translation_manifest.json from selected articles only
→ translate block-by-block with stable Bxxx IDs
→ automatic completeness / duplicate / number checks
→ semantic review only for flagged blocks/articles
→ build EPUB
→ build single-column HTML fallback
→ optional PDF archive only when requested
→ publish to Google Drive weekly folder
```

## State model

Each selected article is independently resumable.

Minimum states:

- pending
- translating
- translated
- review
- pass
- published

The conversation window is never the source of truth for progress. Resume from `translation_manifest.json`.

## Paragraph rule

Source EPUB semantic blocks are the paragraph authority.

- Do not treat layout wrappers such as `div` and `section` as paragraph breaks.
- Preserve one translated output block for each source Bxxx block.
- Do not split a source paragraph into sentence-level paragraphs for presentation.
- Do not merge source semantic blocks during normal translation.
- Interview/Q&A content must preserve source speaker-turn/block boundaries. A rhetorical question inside an answer must not create a new interviewer paragraph.
- Legacy translations may be reflowed against source paragraph boundaries without retranslating content.

## Translation execution

Default throughput path:

- routine faithful translation: Terra · Medium
- difficult ambiguity / idiom / attribution / QA escalation: Sol · High
- deterministic checks: Python, not LLM reasoning

Work in article batches without requiring user "continue" messages.

Selection file example:

```json
{
  "articles": [
    {"publication": "wired", "issue_date": "2026-09-02", "seq": 14},
    {"publication": "economist", "issue_date": "2026-09-19", "seq": 3}
  ]
}
```

Workspace initialization:

```bash
python scripts/magazine_translation_pipeline.py init \
  --readable-root magazine-readable \
  --workspace magazine-workspace \
  --selection selection.json
```

Only selected articles enter the translation manifest.

Queue command:

```bash
python scripts/magazine_translation_pipeline.py next-batch \
  --workspace <workspace> \
  --max-articles 4 \
  --max-blocks 120 \
  --out next_batch.json
```

The next batch is derived from the persisted manifest and QA state, so a new chat/window can resume without replaying completed articles.


## Automation-runtime EPUB materialization (preferred fresh-run path)

For the scheduled weekly controller, the preferred fresh-run path is the Automation execution workspace.

When the authorized mirror exposes the current issue path, byte size and Git blob SHA but the ordinary foreground GitHub connector cannot return the large EPUB binary:

1. first materialize the exact EPUB bytes from `yemoge123/awesome-english-ebooks` into the Automation execution workspace using the runtime's available runtime-native/non-Actions transport;
2. if that path is unavailable or fails, and GitHub Actions quota is available, allow one explicit low-frequency `workflow_dispatch` extraction/materialization fallback for the exact required issue(s);
3. compute actual byte size and canonical Git blob SHA locally;
4. require exact equality with the mirror metadata;
5. only then run the existing EPUB extractor/importer and Stage A/B pipeline;
6. persist the transport receipt with the weekly runtime provenance, including whether Actions fallback was used and the workflow/run identity when applicable.

A foreground-chat inability to download the EPUB must not be promoted to a weekly production blocker. `RUNTIME_SOURCE_MATERIALIZATION_FAILED` may be set only after the Automation runtime attempts the preferred materialization path and, when quota is available and appropriate, the permitted manual Actions fallback.

The transport receipt must retain enough evidence to diagnose/reproduce the route without storing credentials: runtime surface, transport class/name, source repository/ref/path, expected+actual size, expected+actual Git blob SHA, verification, post-materialization extractor/importer path, and embedded-image-binary retention status.

Do not ask the user for a manual upload and do not make Drive an online source-staging dependency merely because the foreground chat connector cannot stream the binary.

### GitHub Actions efficiency

Actions is a fallback accelerator, not the default transport. Use it only when the expected value is material.

- Prefer one manual `workflow_dispatch` over repeated or per-publication runs.
- No scheduled source-extraction Actions.
- Avoid push/PR triggers for heavy extraction; keep push/PR checks lightweight.
- Avoid retry loops, redundant artifact builds, and work that can be done deterministically in the Automation workspace/local scripts.
- Preserve quota for source extraction or release-critical validation that cannot be completed reliably otherwise.

## Verified local EPUB fallback (non-Actions)

When the current authorized EPUB bytes are already available locally, from Google Drive, or from a conversation upload, use the verified local import path instead of GitHub Actions.

Command pattern:

```bash
python scripts/magazine_local_epub_import.py \
  --publication <economist|new_yorker|atlantic|wired> \
  --issue-date YYYY-MM-DD \
  --input /path/to/current.epub \
  --source-file <authorized repo path under the publication root> \
  --expected-source-sha <40-char Git blob SHA from yemoge123/awesome-english-ebooks master> \
  --expected-size <optional exact byte size> \
  --out magazine-readable
```

Hard requirements:
- The importer performs no network I/O.
- It rejects files outside the publication's authorized root.
- It accepts EPUB only.
- It computes the canonical Git blob SHA-1 over the Git object header plus file bytes and requires an exact match with the source SHA observed from the authorized GitHub repository.
- A mismatch blocks extraction and must not be downgraded to PARTIAL.
- After verification, it emits the same article text / semantic block / image mapping structure used by the normal extractor so the existing Stage A/B and translation pipeline can continue unchanged.
- Use this path while GitHub Actions is unavailable or intentionally disabled; do not create a temporary workflow merely to move binary source bytes.

## Mobile output

Priority:

1. EPUB — primary phone reading format.
2. HTML — browser fallback and QA surface.
3. PDF — optional fixed-layout archive only when explicitly requested.

Mobile output requirements:

- single-column reflowable text
- adjustable font size through reader/browser
- dark-mode friendly
- no page-width assumptions
- no sentence-level paragraph fragmentation
- prose paragraphs remain source-paragraph anchored; interviews remain source-turn anchored
- article-level table of contents
- embedded article images only when source mapping is explicit
- periodic runs do not create Google Docs

## Quality gates

Article gate:

- exact Bxxx coverage
- no duplicate block IDs
- block order preserved
- no empty translated blocks
- metadata present
- numeric mismatches flagged

Publication gate:

- selected article count matches manifest
- titles unique
- image references resolvable
- no missing article output

Release gate:

- EPUB package parses
- every EPUB chapter parses as XML/XHTML
- all embedded image references resolve
- HTML index/article relative links resolve
- mobile paragraph-fragmentation audit passes
- Drive upload succeeds

Automated release gate:

```bash
python scripts/magazine_translation_pipeline.py release-check \
  --workspace magazine-workspace \
  --html magazine-mobile-html \
  --epub magazine-mobile.epub
```

A non-zero exit status blocks release.

## Freshness and processed-before handling

Before selection, resolve the current valid authorized issue independently for each publication.

- Do not equate "issue date is older than this week" with stale.
- For monthly/less-frequent publications, an unchanged latest issue remains current if its authorized source SHA is still the latest issue identity.
- If the current issue/source SHA was already fully processed and passed, record `processed_before=true`, retain the source/translation pointer, and do not create a duplicate translation.
- Mark `SOURCE_NOT_FRESH` only when the available extraction is older/different from the publication's current valid authorized issue.
- Weekly packaging may include processed-before pointers in the index/runtime state without pretending they are newly translated articles.

## Current W38 migration lesson

The legacy W38 output showed strong paragraph fragmentation: many translated documents had several times more paragraph nodes than the source EPUB. Future releases must therefore use semantic source blocks before translation, not repair presentation after translation.


## Runtime Data Storage Boundary

GitHub is the authority for executable/version-controlled material only: Android reader source, magazine extraction/translation pipeline code, tests, workflows, authorization policy, translation profile, workflow documentation, schemas, and lightweight Drive pointers.

Google Drive is the canonical authority for translation runtime data: GT batch manifests and working state, source-recovery records, translated article bodies, QA payloads, EPUB/HTML ZIP reading packages, images, checkpoints, and superseded runtime artifacts.

Do not commit GT-xxx runtime payloads back into Git. For reproducibility, each Drive batch should retain the relevant repository HEAD or code/profile blob/commit SHA together with source EPUB path/SHA identity.
