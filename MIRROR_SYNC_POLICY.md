# Mirror Sync Policy

Status: canonical
Effective: 2026-09-30
Repository: `yemoge123/awesome-english-ebooks`
Branch: `master`

## Purpose

This repository has two roles:

1. user-controlled mirror of `hehonghui/awesome-english-ebooks` magazine source files;
2. the single GitHub control plane for periodic magazine translation.

Periodic translation must execute from this repository, not directly from upstream and not from `yemoge123/RssReader`.

## Upstream boundary

- Upstream: `hehonghui/awesome-english-ebooks:master`
- Execution mirror: `yemoge123/awesome-english-ebooks:master`
- Upstream is provenance and source-update origin only.
- Translation execution reads magazine source files and canonical translation-control files from the execution mirror.

## Fork-only control-plane paths

The following paths are owned by the user's mirror and must survive every upstream synchronization:

- `MIRROR_SYNC_POLICY.md`
- `PERIODIC_MAGAZINE_TASK.md`
- `MAGAZINE_TRANSLATION_STRATEGY.md`
- `MAGAZINE_TRANSLATION_PROFILE.md`
- `MAGAZINE_WORKFLOW.md`
- `authorized-input/magazine_policy.json`
- `scripts/magazine_epub_extract.py`
- `scripts/magazine_local_epub_import.py`
- `scripts/magazine_translation_pipeline.py`
- `scripts/test_magazine_epub_extract.py`
- `scripts/test_magazine_local_epub_import.py`
- `scripts/test_magazine_translation_pipeline.py`
- `.github/workflows/magazine-repo-reader.yml`
- `backfill/README.md`
- the periodic-translation section of `README.md`

## Freshness gate

Before each weekly translation run:

1. read current upstream master head;
2. read current execution-mirror master head;
3. determine whether the execution mirror already contains the current upstream source state;
4. if yes, continue;
5. if the mirror is behind/diverged only because the mirror has fork-only control-plane commits, perform safe synchronization before selecting the current issue;
6. if safe synchronization cannot be proven, stop with `MIRROR_NOT_FRESH`; do not silently translate directly from upstream.

## Safe synchronization

Never force-reset the mirror to upstream.

Preferred semantic operation:

1. use the current upstream tree as the source-content base;
2. overlay/preserve every fork-only control-plane path listed above from the current execution mirror;
3. create a merge commit with:
   - first parent = current execution-mirror head;
   - second parent = current upstream head;
4. fast-forward `yemoge123/awesome-english-ebooks:master` to that merge commit.

If upstream introduces a path that conflicts with a fork-only control-plane path, classify it as a real merge conflict and stop for reconciliation; do not guess.

## Post-sync read-back

After synchronization verify:

- current required magazine issue paths exist in the execution mirror;
- `authorized-input/magazine_policy.json.source_repo == "yemoge123/awesome-english-ebooks"`;
- `scripts/magazine_epub_extract.py` uses `SOURCE_REPO = "yemoge123/awesome-english-ebooks"`;
- all canonical control-plane files exist;
- no periodic translation dependency points to `yemoge123/RssReader`;
- upstream remains provenance only.

## Actions boundary

The manual magazine workflow is optional maintenance infrastructure, not the weekly scheduler. Do not dispatch it while the user's current GitHub Actions usage restriction remains in force.

## Runtime-data boundary

Weekly manifests, translations, QA payloads, checkpoints, EPUB/HTML packages and source payload persistence belong to the current execution workspace and Google Drive according to `MAGAZINE_TRANSLATION_STRATEGY.md`. Do not commit weekly runtime data to Git.

## Do not repeat

- Do not restore periodic translation assets into RssReader.
- Do not make personal-ai-context a second canonical copy.
- Do not translate directly from upstream merely because the mirror is stale.
- Do not force-reset the mirror and lose fork-only control-plane files.
