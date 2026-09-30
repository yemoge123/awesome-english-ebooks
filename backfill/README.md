# Translation Runtime Data

Translation/backfill **runtime data is not stored in this repository**.

## Canonical data authority

Google Drive is the canonical store for:

- GT batch manifests and working state
- source-recovery requests and source identity records
- translations and checkpoints
- QA results
- EPUB / HTML ZIP reading packages
- superseded translation artifacts

Current GT-016 working location:

- Drive folder: https://drive.google.com/drive/folders/1QZ2xnKg0O3U0BBgUkOQ1iG9iUxyCq8tl
- Source recovery record: https://docs.google.com/document/d/13HeN0YcMcpTT_Xzq2E_GayW6TR7IX6tahn11HPgTwhg/edit

## Repository boundary

This repository is the magazine source mirror and GitHub control plane. It keeps source issues plus executable/version-controlled contracts:

- magazine source mirror
- magazine extraction / translation pipeline code
- tests
- workflows
- authorization policy
- translation profile / workflow documentation
- schemas and lightweight pointers such as this file

Do not add GT-xxx manifests, translation checkpoints, translated article bodies, QA payloads,
EPUBs, HTML ZIPs, images, or other batch runtime data back into Git.

For reproducibility, Drive batch records should retain the relevant Git commit/SHA of the
translation profile, extractor, pipeline, and source EPUB identities.
