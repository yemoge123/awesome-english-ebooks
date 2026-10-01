# Magazine Translation Profile v1

> Canonical operating strategy: `MAGAZINE_TRANSLATION_STRATEGY.md` (vNext.3). This profile defines translation fidelity/typography details; strategy-level scope, interest gating, queue semantics, package shape, and runtime-authority decisions come from the strategy file.

## Purpose
Canonical rules for personal magazine translation runs.

## Translation
- Translate faithfully and completely into Simplified Chinese.
- Do not summarize, comment, explain, editorialize, or silently omit examples.
- Preserve attribution, uncertainty, modality, dates, numbers, names, quotations, and paragraph order.
- Do not split one source semantic block into many short paragraphs unless the source block itself contains explicit line breaks.
- Do not merge adjacent source blocks during translation.
- For interviews/Q&A, source EPUB speaker-turn/block boundaries are authoritative. Preserve interviewer questions and respondent answers as distinct blocks; do not infer turn boundaries from Chinese question marks alone.
- Return exactly one translated block for every source block ID.
- Preserve block IDs unchanged.

## Naming
- Keep widely used company/product names in their common Latin form when that is clearer: OpenAI, Nvidia, AMD, WIRED.
- For personal names, preserve the original Latin name when a Chinese rendering is uncertain.
- Never invent a Chinese name.

## Metadata
Every selected article retains:
- publication
- issue date
- translated title
- original title
- author when available
- source EPUB path / URL
- source SHA where available

## QA gates
An article may be published only when:
- the complete source article has been read from the authorized repository artifact;
- every source block ID appears exactly once in translation;
- there are no extra translation block IDs;
- source first/last blocks and all explicit headings have corresponding translated blocks;
- title and source metadata are present;
- dates, numbers, percentages, money, proper names, quotations, and important examples have no unresolved semantic mismatch;
- numeric QA normalizes equivalent Chinese date, currency, percentage, and multiplier expressions before raising a mismatch;
- the article has no unresolved review flag.

## Historical revalidation
- Historical Reader/QA artifacts are evidence, not automatic current-rule certification.
- A legacy PASS must not be promoted to the current completeness PASS unless the authorized source article is available and the current QA gates are rerun.
- Recovered translations may be marked `RECOVERED_TRANSLATION_SOURCE_REVERIFY_REQUIRED` while source text is unavailable.
- Historical backfill must not re-screen an already locked batch unless the batch contract itself is explicitly reopened.

## Chinese typography
- Normal Chinese body paragraphs use a first-line indent of two em (`text-indent: 2em`).
- Canonical EPUB body rhythm is mobile-first: about `line-height: 1.64`, compact paragraph gap about `0.38em`, and minimal horizontal EPUB padding (about `0.3em`).
- The reader app owns the outer page margin. Do not stack large EPUB padding/margins on top of the reader margin.
- Front matter such as author/date/category/byline/caption/source/note does not use body indentation.
- Lists, blockquotes, captions, headings, code/preformatted text, and metadata do not use first-line body indentation.
- Body paragraph spacing stays compact; do not simulate paragraph separation by inserting extra blank paragraphs.
- Legacy desktop-oriented values such as `padding: 2rem`, `margin: 5%`, or body `line-height >= 1.8` are release-blocking.

## Reading output
- Google Drive remains the archive.
- Primary mobile output is EPUB with reflowable text, adjustable font size, and reader-app dark mode.
- Single-column HTML is the browser fallback and QA surface; archive the browser reading surface as an HTML ZIP alongside the EPUB.
- Do not generate Google Docs for periodic magazine translation runs.
- PDF is optional and is generated only when explicitly requested or needed for fixed-layout archival review.
