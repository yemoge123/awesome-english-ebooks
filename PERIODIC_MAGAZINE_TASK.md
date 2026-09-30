# Periodic Magazine Translation Controller

Status: canonical task-entry contract  
Repository: `yemoge123/awesome-english-ebooks`  
Branch: `master`  
Effective: 2026-09-30

## Repository boundary

This repository is the single GitHub control plane for periodic magazine translation and the user's authorized magazine-source mirror.

- Periodic translation MUST read source issues, policy, scripts, tests and workflow contracts from this repository.
- `hehonghui/awesome-english-ebooks` is mirror-upstream provenance only. Normal periodic execution MUST NOT depend on reading the upstream repository directly.
- `yemoge123/RssReader` is an independent Android reader project. Periodic magazine translation MUST NOT read strategy, code, tests, authorization policy or workflow state from RssReader.
- Google Drive is the durable persistence, delivery and recovery authority after current-run artifacts are written there. Drive is not a prerequisite for a fresh weekly source-extraction/translation run.

## Mandatory read order

At the start of every weekly run, read the current `master` versions in this repository:

1. `MIRROR_SYNC_POLICY.md` — fork freshness/synchronization gate.
2. `MAGAZINE_TRANSLATION_STRATEGY.md` — highest translation authority.
3. `MAGAZINE_TRANSLATION_PROFILE.md` — fidelity and typography.
4. `MAGAZINE_WORKFLOW.md` — executable workflow.
5. `authorized-input/magazine_policy.json` — authorization/source boundary.

If any older prompt, Drive handoff, chat history or compatibility pointer conflicts with these files, this repository wins.

## Mirror freshness gate

Before resolving any current issue, execute `MIRROR_SYNC_POLICY.md`. Translation source selection may begin only after the user's fork contains the required upstream source state while preserving the fork-only control plane. Do not silently translate directly from upstream when the mirror is stale.

## Weekly execution

Fixed publications:

- The Economist
- WIRED
- The Atlantic
- The New Yorker

Canonical execution path:

```text
yemoge123/awesome-english-ebooks
  -> current automation execution workspace
  -> source extraction / semantic blocks
  -> Stage A recall
  -> Stage B full-body relevance
  -> exact-body / lineage reuse
  -> residual faithful translation
  -> L0/L1/L2 QA as required
  -> one combined EPUB + one combined HTML ZIP + reading index
  -> Google Drive persistence + read-back
```

Do not require the user to manually upload EPUBs when the automation execution environment can materialize the authorized mirror source. Do not route source acquisition through RssReader.

## Source identity

The source repository for execution is `yemoge123/awesome-english-ebooks`.

For every issue used, persist:

- publication
- issue date
- mirror repository path
- mirror commit/ref when available
- Git blob SHA
- byte size
- body/source fingerprint where applicable
- processed-before/reuse status

The upstream repository identity may be retained as provenance metadata, but it is not an execution dependency.

## Automation source-materialization contract

For fresh weekly execution, large EPUB binary transport belongs to the **automation execution runtime**, not to the foreground chat connector.

Hard rules:

- A foreground/chat GitHub connector being unable to return large binary bytes is **not** evidence that the production weekly source gate failed.
- When path / byte size / Git blob SHA are visible but the binary payload is not, the weekly Automation should first use its available runtime-native/non-Actions source-materialization path to place the exact mirror bytes into the current execution workspace.
- The user must not be asked to manually upload the EPUB, and Google Drive must not be introduced as a mandatory pre-extraction staging hop.
- After materialization, verify `actual_size == expected_size` and `actual_git_blob_sha == expected_git_blob_sha` before extraction. A mismatch is a hard source failure.
- If runtime-native/non-Actions materialization is unavailable or fails, GitHub Actions may be used as a **low-frequency manual fallback** when quota is available, preferably a single explicit `workflow_dispatch` source-extraction run for the exact needed issue(s).
- A true production blocker may be declared only after the **automation execution runtime** itself attempts the preferred runtime-native path and, when applicable/available, the permitted manual Actions fallback. Use `RUNTIME_SOURCE_MATERIALIZATION_FAILED`; do not infer this state from a foreground chat limitation.
- GitHub Actions usage must be quota-efficient: no scheduled extraction, no retry loops, no fan-out by publication when one run can cover the required issues, and no low-value push/PR triggers for source extraction.

Every successful materialization must persist a **transport receipt** in current-run provenance and final Drive control/source state. The receipt must include:

- `transport` / transport class used by the runtime;
- execution surface (`automation_runtime`);
- mirror repository, ref/commit and repo path;
- expected and actual byte size;
- expected and actual Git blob SHA;
- verification verdict;
- extractor/importer path used after materialization;
- whether embedded source image binaries were retained;
- run timestamp / ISO week.

Do **not** persist signed download URLs, cookies, tokens, credentials or other ephemeral secrets. If the runtime uses an internal/opaque transport implementation, record that fact plus the verifiable inputs/outputs above; do not reduce the receipt to an unexplained label only.

## Reuse and freshness

Apply the rules in `MAGAZINE_TRANSLATION_STRATEGY.md`:

- freshness is publication-cadence aware;
- unchanged current monthly issues remain valid;
- exact previously-PASS bodies are reused rather than retranslated;
- selected-article loss must remain zero;
- no artificial weekly article quota is allowed.

## Output

Each weekly translation run produces one combined reading package:

- `00_阅读索引`
- `YYYY-Www_外刊忠实翻译.epub`
- `YYYY-Www_外刊忠实翻译_HTML.zip`
- control/source/translation/QA/package-state payloads required for recovery
- `90_历史归档/` only for superseded formal releases

Periodic magazine translation is not an RSS/Supabase publishing workflow. RSS/RssReader delivery is a separate system unless the user explicitly requests a separate integration later.

## Completion gate

`WEEKLY_COMPLETE` requires the current strategy's completion gate, including:

- all selected articles PASS/PUBLISHED;
- remaining queue = 0;
- EPUB/HTML release checks PASS;
- applicable image checks completed or explicitly recorded as an accepted limit without overstating completeness;
- Drive upload/read-back PASS.

## GitHub Actions boundary

GitHub Actions is allowed as an **on-demand fallback/maintenance path**, not as the weekly scheduler.

Quota-efficiency rules:
- prefer runtime-native/non-Actions materialization when it works reliably;
- use explicit `workflow_dispatch` only when it materially reduces manual work or resolves a real source-materialization blocker;
- batch the exact required issue(s) into as few runs as practical;
- do not schedule periodic extraction Actions;
- avoid low-value push/PR triggers, repeated retries, matrix fan-out, duplicate artifact builds, or validation that can run locally/deterministically;
- preserve Actions quota for source extraction, release-critical checks, or other high-value jobs that cannot be completed reliably in the current execution runtime.

## Do not repeat

- Do not restore periodic magazine strategy/scripts/tests/workflows under `yemoge123/RssReader`.
- Do not maintain a second canonical copy in `personal-ai-context`; legacy paths there are compatibility pointers only.
- Do not make the upstream mirror source the normal direct execution dependency.
- Do not treat Drive as an online source-staging requirement for a fresh weekly run.


## Google Drive target identity

Drive persistence uses stable IDs first and human-readable names second.

- weekly work root: `AI周期检索资料`, folder id `1Uk35QUG4IUxrkHSx_g9xfXOH54g3abZV`
- weekly container: `20_Weekly`, folder id `1kZx08i_9dzxz71iu2TrfujgZx2TkAz1a`
- final reader archive: `China_News_Archive`, folder id `1p8bG3Bq53Md66REL3JotJzIS14SBvlkO`
- final weekly EPUB destination: `02_Chinese_Reader`, folder id `1x8iY_rTXIbd17RfG1FPwKZXeENQkgllv`
- human entry document: `00_START_HERE_最终译刊入口_先看这里`, file id `1K_YFVjCTyvE3383svJVwfaqv5tfvFhkqjNImOYes2Mo`

Automation MUST resolve these destinations by Drive file/folder ID when available. Folder names are human-readable aliases and MUST NOT be used to silently create replacement folders if a display name changes. After publishing the final EPUB, read back metadata and require the parent id to equal `1x8iY_rTXIbd17RfG1FPwKZXeENQkgllv`.

The human entry document is navigation only, never a state or data authority. Do not make the weekly pipeline depend on its prose content.
