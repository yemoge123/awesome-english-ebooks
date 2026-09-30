# Mirror Sync Policy

Status: canonical  
Effective: 2026-09-30

## Purpose

Keep `yemoge123/awesome-english-ebooks` current with its GitHub fork parent `hehonghui/awesome-english-ebooks` while preserving the user's periodic-translation control plane in the fork.

The upstream repository is a synchronization/provenance source only. Translation execution always reads magazine issues from the user's fork after this gate passes.

## Weekly pre-run gate

Before resolving current magazine issues:

1. Read the fork parent identity and current upstream `master` commit.
2. Read the current `yemoge123/awesome-english-ebooks:master` commit.
3. Compare ancestry.
4. If the fork already contains the upstream commit, continue without writing GitHub.
5. If the fork is behind/diverged because of target-only control-plane commits, synchronize before source selection.

## Safe synchronization invariant

The fork contains target-only control-plane paths that MUST survive upstream synchronization:

- `README.md` control-plane appendix
- `PERIODIC_MAGAZINE_TASK.md`
- `MAGAZINE_TRANSLATION_STRATEGY.md`
- `MAGAZINE_TRANSLATION_PROFILE.md`
- `MAGAZINE_WORKFLOW.md`
- `MIRROR_SYNC_POLICY.md`
- `authorized-input/magazine_policy.json`
- `.github/workflows/magazine-repo-reader.yml`
- `backfill/README.md`
- `scripts/magazine_epub_extract.py`
- `scripts/magazine_local_epub_import.py`
- `scripts/magazine_translation_pipeline.py`
- `scripts/test_magazine_epub_extract.py`
- `scripts/test_magazine_local_epub_import.py`
- `scripts/test_magazine_translation_pipeline.py`

Safe sync semantics:

- use the current upstream `master` tree as the source-content base;
- overlay the current fork versions of the target-only control-plane paths above;
- for `README.md`, retain the latest upstream README body and the fork's periodic-translation control-plane appendix;
- create a merge commit whose parents include the current fork head and the upstream head;
- advance fork `master` by fast-forward to that merge commit;
- never force-reset fork `master` to upstream and thereby discard the control plane.

## Verification

After sync, verify:

- the fork contains the upstream head in ancestry;
- the current required issue directories/files are present in the fork;
- all target-only control-plane files remain present;
- `authorized-input/magazine_policy.json.source_repo == "yemoge123/awesome-english-ebooks"`;
- `scripts/magazine_epub_extract.py` reads `SOURCE_REPO = "yemoge123/awesome-english-ebooks"`;
- RssReader is not referenced as an execution dependency.

Only after this verification may the weekly source freshness/selection gate proceed.

## Actions boundary

This sync policy does not require GitHub Actions. While the user's current Actions restriction is active, do not dispatch or create scheduled sync workflows. Use the connected GitHub repository operations available to the execution environment.

## Failure handling

If the mirror cannot be synchronized safely:

- mark `MIRROR_NOT_FRESH`;
- do not silently fall back to translating directly from the upstream repository;
- preserve the weekly recurrence;
- record the upstream head, fork head, missing issue identity, and exact blocker.
