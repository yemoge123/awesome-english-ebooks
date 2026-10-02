# Periodic Magazine Translation Strategy vNext.3

## Authority

This file is the canonical strategy contract for the periodic faithful-translation workflow.
It governs source scope, interest selection, queue semantics, QA layers, reading-package shape,
runtime authority, and long-term execution behavior.

Implementation-specific translation fidelity rules remain in `MAGAZINE_TRANSLATION_PROFILE.md`.
Executable workflow details remain in `MAGAZINE_WORKFLOW.md`.

Repository boundary (2026-09-30): the canonical GitHub control plane and authorized source mirror for this workflow is `yemoge123/awesome-english-ebooks` on `master`. Mirror freshness and safe upstream synchronization are governed by `MIRROR_SYNC_POLICY.md` and must pass before weekly source selection. The upstream repository `hehonghui/awesome-english-ebooks` is provenance for the mirror only; periodic translation execution must read source identity, policy, scripts, tests and workflow rules from `yemoge123/awesome-english-ebooks`. `yemoge123/RssReader` is an Android reader project and is not part of periodic magazine translation execution.

## 1. Fixed publication scope

Always scan all four publications:

| Publication | Role | Scan | Selection gate |
| --- | --- | --- | --- |
| The Economist | Core source | Full issue | Relatively broad |
| WIRED | Core technical source | Full issue | Relatively broad |
| The Atlantic | High-selectivity source | Full issue | Strict |
| The New Yorker | High-selectivity source | Full issue | Strict |

No publication is removed. The New Yorker and The Atlantic are not low-quality sources; they are lower-density sources for the user's interests and therefore use stricter selection.

## 2. No artificial translation quota

There is no hard article-count or source-word quota.

Every article that passes the final high-value interest gate enters the full-translation queue.
Large weeks are handled by resumable batches and continuation, not by dropping already-qualified articles.

Core metric: selected-article loss = 0.

## 3. Interest model

### P0 — Core
- AI / AGI / LLM / AI Agent
- semiconductors / chips / CPU / GPU / accelerators
- EDA / AMS / SerDes / verification
- software and engineering automation
- China as a substantive article theme
- China technology / manufacturing
- US-China relations and technology competition
- trade war / tariffs / export controls / supply chain
- industrial policy
- major politics / geopolitics

### P1 — Extended
- robotics
- data centers / AI energy infrastructure
- software engineering / programming languages
- technology-company strategy and competition
- technical management / engineering productivity
- scientific-research systems
- manufacturing competition / business models / technology policy

### P2 — High-value long reading
- major political deep dives
- important economic structural change
- major international relations
- durable institutional/social change
- high-quality investigations with long-term explanatory value

Default low priority unless materially connected to P0/P1/P2:
entertainment, fashion, sports, travel, celebrity life, ordinary lifestyle/consumer culture,
ordinary health, and general cultural/literary commentary.

China is a valid interest in its own right when it is a substantive theme; incidental mentions do not pass.

## 4. Two-stage interest gate

### Stage A — Recall first
Scan all four issues with no candidate-count cap using title, subtitle/deck, section, entities,
keywords, metadata, and body semantic signals. Produce `INTEREST_CANDIDATE`.

### Stage B — Full-body relevance
Read the candidate body and decide whether it materially satisfies P0/P1/P2.
Reject incidental mentions, contents/cover pages, short blurbs, low-information items, and keyword false positives.
Only passing articles become `SELECTED_FOR_FULL_TRANSLATION`.

## 5. Cross-issue deduplication

Before translation, detect duplicates/reprints using:
- source SHA
- normalized title
- body fingerprint
- near-duplicate comparison

If the body is materially the same, translate once while retaining every publication/issue/source pointer.

## 6. Persistent no-loss queue

State model:

`DISCOVERED -> CANDIDATE -> SELECTED -> QUEUED -> TRANSLATING -> TRANSLATED -> QA_REVIEW -> PASS -> PUBLISHED`

Selected articles are never dropped because a new week arrives.
Queue priority combines P0/P1/P2 priority with age so older qualified work cannot starve.

The conversation window is never a checkpoint.

## 7. Batch execution

Default execution unit:
- approximately 4 articles, or
- approximately 120 source semantic blocks,
whichever reaches a natural boundary first.

This is an execution batch size, not a weekly quota.
A long article is never truncated to satisfy a batch limit.

After each batch, persist translation files, manifest state, QA state, remaining queue,
source identity, and relevant code/profile version pointers.

## 8. Translation-efficiency architecture

Use capability roles rather than permanently binding policy to one model name:

- `FAST_FAITHFUL_TRANSLATOR`: routine faithful block-by-block translation
- `HIGH_REASONING_TRANSLATOR`: technical density, complex politics/trade, ambiguity, idiom,
  attribution, important quotations, or complex numeric logic
- `HIGH_REASONING_REVIEWER`: escalated semantic QA and critical P0 review
- deterministic Python checks for structural QA

Efficiency comes from batch execution, deterministic QA, model escalation only when needed,
dedupe, terminology reuse, and resumability — not from dropping high-value articles.

## 9. Translation memory / terminology

The current weekly execution workspace may maintain:
- `terminology.json`
- `translation_memory.json`

Previously persisted Google Drive terminology / translation memory may be loaded as an optional
cross-week optimization, but Drive availability must not block a fresh weekly translation run.
Current-run terminology state travels with the final persistence payload.

Use these files for company/person/product/technical/policy/institution terminology and confirmed renderings.
They improve speed and cross-week consistency but must not override context mechanically.

## 10. Source payload persistence

For every selected article, retain enough authorized source payload in the current execution workspace
to run completeness QA:

- source metadata
- source article text
- semantic source blocks / stable block IDs
- source EPUB path and SHA
- image mapping

Do not require source EPUBs or selected source payloads to be staged in Google Drive before extraction,
selection, translation, QA, or package build.

At final publication, persist the selected source payload and provenance with the weekly package in
Google Drive. If a run must span executions or needs interruption recovery, an earlier Drive checkpoint
may be written as a recovery aid; that checkpoint is optional for a single uninterrupted weekly run.

Do not rely on a three-day GitHub artifact as the only durable copy after publication.


### Source-materialization evidence

For scheduled fresh runs, source-byte materialization is an Automation-runtime responsibility. A foreground chat/connector limitation is not a source-freshness or source-availability failure. Runtime-native/non-Actions materialization is preferred, but a low-frequency manual GitHub Actions `workflow_dispatch` fallback is allowed when it materially resolves a real blocker and quota is available.

After every successful Automation-runtime materialization, persist a transport receipt alongside provenance with at least: transport class/name, execution surface, mirror repo/ref/path, expected/actual byte size, expected/actual Git blob SHA, verification verdict, extractor/importer path, and embedded-image-binary retention status. Ephemeral signed URLs and credentials must never be persisted.

If the runtime's concrete transport implementation is internal or opaque, persist that limitation explicitly together with the verifiable input/output evidence. This prevents a future run from treating an unexplained transport label as a reproducible implementation.

Only after the Automation runtime attempts the preferred materialization path and, when appropriate/available, the permitted manual Actions fallback may it set `RUNTIME_SOURCE_MATERIALIZATION_FAILED`. Do not ask the user to upload the issue merely because the foreground chat connector cannot stream large binary files.

## 11. Source freshness gate

`latest successful artifact` is not automatically `CURRENT_VALID_SOURCE`.

Freshness is publication-cadence aware. A weekly controller must determine the current valid issue independently for each publication. An unchanged current monthly issue is still current when its issue identity/source SHA remains the latest authorized source; age alone does not make it stale.

Validate:
- authorized_input
- publication
- publication cadence / current valid issue identity
- issue_date
- source_file
- source_sha
- artifact run identity
- freshness relative to that publication's current valid issue
- whether the exact issue/body was already processed

If the latest authorized issue for a publication is identical to an already processed source SHA/body fingerprint, mark it as `CURRENT_VALID_SOURCE / PROCESSED_BEFORE` and reuse the prior PASS translation/source pointer rather than retranslating it.

Use `SOURCE_NOT_FRESH` only when the available extraction does not represent that publication's current valid authorized issue. Do not require every publication to publish a new issue every week, and do not repackage an older superseded issue as a new week.

## 12. QA layers

### Level 0 — Deterministic
Check block count/IDs/order, duplicate/extra/missing/empty blocks, metadata, first/last blocks,
explicit headings, image references, and package structure.

### Level 1 — Semantic QA for every article
Check obvious omission/compression, attribution, important entities/quotes/examples, and numeric meaning.

### Level 2 — High-reasoning QA
Apply to P0 core articles, technically dense pieces, major politics/trade/policy pieces,
long investigations, complex numeric relationships, and Level-1 flagged articles.

## 13. Numeric semantic normalization

Numeric QA must compare meaning, not raw token strings.
Normalize dates, percentages/percentage points, currencies, thousand/million/billion/trillion,
Chinese 万/亿 units, multipliers, and temperatures before escalating a mismatch.

Only genuine semantic/value mismatches are review failures.

## 14. Reading package — HARD RULE

Each weekly run has one combined reading package across all four publications:

- `00_阅读索引`
- `YYYY-Www_外刊忠实翻译.epub`
- `YYYY-Www_外刊忠实翻译_HTML.zip`
- `90_历史归档/`

Do not create four separate publication EPUBs or four separate publication HTML ZIPs by default.

EPUB internal organization:
- publication-level sections
- article-level table of contents uses Simplified Chinese translated article titles
- visible article headings use the same Chinese translated title; retain the original English title separately as metadata/subtitle for traceability
- omit empty publication sections while the reading index still records scan/selected counts

Google Docs and PDF are not default formal reading outputs.

## 15. Reading typography

Use the canonical mobile-first reading profile:
- reflowable single column
- adjustable font size / reader dark mode
- reader app owns the outer page geometry; EPUB must not impose large fixed page margins
- EPUB body target: `margin:0`, horizontal padding about `0.3em`, body `line-height:1.64`
- compact Chinese prose: body first-line indent `2em` with small paragraph gap (about `0.38em`), not large paragraph spacing
- headings, metadata, lists, quotations, Q&A labels not indented
- avoid legacy patterns such as `padding:2rem`, `margin:5%`, or body `line-height>=1.8`
- source-semantic paragraph boundaries
- deterministic source-image placement only
- no sentence-level paragraph fragmentation

Release checks must reject legacy typography tokens and require the canonical mobile profile tokens.

## 16. Rolling package

If a large week is still `IN_PROGRESS`, the current EPUB/HTML package may be rebuilt from all current PASS articles
so the user can read completed work early.

During `IN_PROGRESS`, overwrite the current package rather than archiving every intermediate build.
Only a superseded formal/complete release moves to `90_历史归档`.

## 17. Weekly completion and notification

`WEEKLY_COMPLETE` requires:
- all selected articles are PASS/PUBLISHED
- remaining queue for that weekly selection = 0
- EPUB release checks pass
- HTML link/package checks pass
- image-resolution checks pass
- Drive upload and read-back pass

Send at most one weekly completion email after `WEEKLY_COMPLETE`.
Continuation batches do not send separate emails.

## 18. Scheduling

Current operating schedule:
- Sunday 09:00 Asia/Shanghai — Weekly Translation Controller.
- Magazine Repo Reader source extraction has no scheduled GitHub Actions trigger.

Source extraction and translation are separate stages. The controller first resolves the current valid
authorized issue/source SHA from the source repository or another authorized input and then executes in
the current task workspace.

A persisted Drive checkpoint may be consulted when resuming interrupted work or reusing prior PASS
translations, terminology, or source payload, but Drive availability is not a prerequisite for a fresh
weekly run. Prefer verified local/runtime-native import first. The repository's `workflow_dispatch`
is an allowed low-frequency manual fallback when Actions quota is available and it materially reduces
manual work or resolves a real source-materialization blocker.

## 18.5 Google Drive destination identity

Drive delivery targets use **stable folder IDs first** and display names second.

- weekly work root `AI周期检索资料`: `1Uk35QUG4IUxrkHSx_g9xfXOH54g3abZV`
- weekly container `20_Weekly`: `1kZx08i_9dzxz71iu2TrfujgZx2TkAz1a`
- final reader archive `China_News_Archive`: `1p8bG3Bq53Md66REL3JotJzIS14SBvlkO`
- final weekly EPUB destination `02_Chinese_Reader`: `1x8iY_rTXIbd17RfG1FPwKZXeENQkgllv`

Human-facing names may be improved without changing pipeline identity. Automation must resolve by Drive ID when available, must not create a replacement folder merely because a display name changes, and must read back final EPUB metadata to confirm its parent id is exactly `1x8iY_rTXIbd17RfG1FPwKZXeENQkgllv`.

The human navigation document in `China_News_Archive` is `00_START_HERE_最终译刊入口_先看这里` (file id `1K_YFVjCTyvE3383svJVwfaqv5tfvFhkqjNImOYes2Mo`). It is navigation only and is never a state/data authority.

## 19. Execution / persistence authority boundary

GitHub / `yemoge123/awesome-english-ebooks` owns:
- the authorized magazine source mirror
- code
- tests
- workflows
- schemas
- translation profile
- interest/selection policy
- authorization policy

The current execution workspace owns transient current-run state while a weekly task is executing:
- current-run manifest / selection / queue
- selected source payloads
- in-progress translations
- QA state
- current-run terminology / translation memory
- package build state

Google Drive is the durable persistence, delivery, and recovery authority after data is written there:
- published weekly manifest / selection / queue
- persisted selected source payloads
- PASS translations
- final QA payloads
- terminology / translation memory snapshots
- EPUB / HTML ZIP and reading index
- optional interruption checkpoints
- historical reading releases

Drive is not an online execution dependency. A fresh weekly run may complete source extraction,
selection, translation, QA, and package build without reading or writing Drive; final publication then
uploads the durable payload and performs Drive read-back. Drive may be used earlier when resumability
or cross-week reuse materially benefits the run.

`magazine-readable` is source-extraction evidence/input, not durable translation authority.

## 20. Actions-efficiency rules

GitHub Actions is permitted, but quota is treated as a scarce shared resource.

- Matching push/PR changes run lightweight tests only.
- Full magazine extraction runs only on explicit `workflow_dispatch`; there is no scheduled extraction.
- Prefer runtime-native/non-Actions materialization when reliable.
- Use Actions when it materially reduces manual work, resolves a real binary/source blocker, or provides release-critical validation unavailable elsewhere.
- Batch exact required issue(s) into as few runs as practical.
- Avoid low-value triggers, retry loops, per-publication fan-out, duplicate artifacts, and checks that can run locally/deterministically.
- There is no RssReader / Android CI coupling. Magazine translation code and source-mirror changes live in `yemoge123/awesome-english-ebooks`.

## 21. Health metrics

Track:
- scanned / candidate / selected / translated / PASS / published / remaining
- selected-article loss
- oldest queued article age
- missing/duplicate block failures
- numeric true mismatch rate
- terminology drift
- semantic escalation rate
- EPUB parse / TOC / HTML-link / image-reference / mobile-fragmentation status

## 22. Implementation status at strategy freeze

### Implemented
- four-publication authorized repo-only extraction contract
- stable semantic source blocks
- resumable translation manifest
- default 4-article / 120-block next-batch logic
- structural block/order/empty QA
- EPUB + HTML builder
- mobile typography and dark-mode-friendly CSS
- image mapping from EPUB internal assets
- Drive as durable persistence / delivery boundary
- periodic magazine workflow fully decoupled from the RssReader / Android repository
- historical issue extraction support
- verified local EPUB ingest with authorized-root and exact Git blob SHA provenance verification

### Policy adopted but implementation still required
- explicit P0/P1/P2 two-stage selection machinery
- body-fingerprint / near-duplicate detection
- durable no-loss continuation worker across runs/weeks
- selected source-payload persistence to Drive
- terminology / translation-memory runtime
- full numeric semantic normalization
- Level-1/Level-2 semantic QA automation
- automatic lightweight `00_阅读索引`
- rolling-package state semantics
- single-email-on-WEEKLY_COMPLETE enforcement
- freshness gate as a hard executable gate

Do not claim these pending items are implemented until code/runtime evidence exists.
