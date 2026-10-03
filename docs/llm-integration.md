# LLM connection and correction review

The additional experimental [LM likelihood](lm-likelihood.md) method has its
own installed-GGUF selection and isolated llama.cpp worker. The chat adapter
below is not used for its candidate search or numerical evaluation.

`llmconfig.py` owns the versioned host-local `config/llm.json`. Missing,
malformed and unknown-version configurations load as unconfigured. Credentials
are kept/replaced/cleared explicitly, saved with mode 0600 and excluded from
source, releases, status and prefs. An opaque session connection ID binds the
saved destination to the connection shown before a deliberate review click.

`settingspage.py` gates endpoint, credential, adapter and skill-install changes
on the host. Any admitted device may discover models at the saved endpoint,
select an exact model ID and test the saved connection. Model-only save accepts
no other fields and preserves the endpoint/key. Feature bodies cannot override
saved connection settings. The browser interface owns these controls; mobile
reader paths are unchanged.

`llmadapter.py` provides shared standard-library HTTP, model discovery, plain
and structured generation. Preset labels supply defaults, not correction code.
No inference library is installed, no weights are fetched and no endpoint is
started. Saved Studio profiles explicitly load already cached GGUF files through
the native API, after offline inventory/variant/path checks; source paths stay
inside the adapter. Loaded model/options/context and public ID are verified.
Failed or unconfirmed loads persist as pending and block generation. HTTP does not follow redirects or proxy environment settings. Each
request has a wall-clock deadline and its own cancellation token; timeout closes
that request without cancelling subsequent sentences. User cancellation aborts
the active socket. Errors expose static categories/status, never response bodies,
prompts or credentials. Connection testing uses synthetic short text and does
not measure language accuracy.

The optional `unsloth-agent-skills` adapter adds the native Skills catalog/create
API and generation with only `read_skill` enabled and MCP disabled. Generic
compatible endpoints use short prompts. The review page offers a portable skill
zip, an explicit install action (never overwriting an existing skill), readiness
check and opt-in skill invocation. Instructions live in
`lib/asrskill/parseh-asr-correction/SKILL.md`; skills are instructions loaded by
the endpoint, not training. No other local tools are enabled by Parseh.

`asrcorrection.py` owns immutable evidence, short sentence prompts and validated
word substitutions. Original Whisper scores remain nullable and are never
replaced by an aligner's confidence. Genuine alternatives are exposed through
the worker capability hook; pinned faster-whisper currently reports alternatives
unavailable. Stable segment/word IDs and Unicode code-point offsets stay local.
Only a bounded target caption, nearby read-only context, language and
flagged-word scores/available hints are sent. Audio, IDs, paths, cookies and unrelated history are excluded.

The model returns a complete plain sentence, not JSON. Local diff mapping accepts
only unambiguous substitutions belonging to selected low-score words. Changes
outside those words, ambiguous boundaries, oversized replacements and deletions
are ignored and disclosed. No model-created certainty/rationale is fabricated.
Unchanged words are unresolved, not proven correct. A sentence failure is local;
remaining sentences continue. Results include failed/unresolved word IDs, and
progress counts attempted suspect words, including failed attempts. A retry
selects only the remaining suspect IDs, retaining other validated proposals.
Cancellation or source/connection changes invalidate in-flight work globally.

The optional `full` task checks all mapped words with its own short prompt and
`parseh-asr-audit` skill. Local character diffs expand to contiguous stable ASR
word boundaries (maximum eight pieces/200 characters), including high-score
pieces. Broad rewrites, unmapped/overlapping spans, changed punctuation and
cross-caption edits are refused. Per-piece evidence and original offsets remain
available. A failed caption never discards other valid caption results.

`review_models` binds each task to a model ID and optional saved profile. Any
admitted browser can change these model-only choices, retaining endpoint/key.
The explicit `review-prepare` action checks the opaque connection revision and
loads only that task's saved installed Studio profile. No transcript is sent
while preparing. Cancel suppresses generation after preparation; an endpoint
model load already started may finish. A subsequent review request checks the
new revision and source. Changing configuration invalidates previous proposals.

Jobs add `review: {evidence, choice, correction, result, diagnostics}` to existing
fields. ASR ends in `awaiting-review-choice`, after releasing runtime/model holds.
Review itself claims the single slot only while correcting. The explicit
`review` / `retry-review` routes bind source and connection IDs. Completed runs
with failed sentences release the slot and expose their failure count.

Bounded prompts, final/raw text, endpoint-supplied reasoning, finish reason and
elapsed time are inspectable through the job result only. These diagnostics stay
in ephemeral job memory (512 KiB / 100 records, 16 KiB per response field), never
logs, status, prefs or sync. Exact saved credentials are redacted from output.
Output-limit retries enlarge the bounded answer budget once before marking only
that sentence failed. Skill mode diagnostics show the invocation, not an invented
claim that the endpoint actually read a skill when no evidence is returned.

`use {job, source_sha256, decisions, manual_edits}` applies chosen candidates or
literal keyboard edits to exact source spans. A manual edit may target any
reviewable word, including those with no score, alternatives or LLM suggestion.
Unknown IDs, overlapping decisions/manual edits, control characters, empty or
oversized substitutions are rejected. Single-word manual edits disallow spaces;
an explicitly selected multi-piece proposal can be typed as a short span. Caption clocks/boundaries are
checked against the original. Changed word timings use the existing timing
editor and need review because retained audio has already been deleted.

`asrreview.js` keeps accepted/manual edits in a pending Unicode-safe draft,
provides accessible details, response inspection and one retry button excluding
accepted/manual words. `addstt.js` owns stale transcript/source/language/model
guards and the only explicit Use handoff with overwrite confirmation. ASR
completion and remembered defaults never send a request or populate the box.

Offline fake HTTP/worker coverage is in `tests/test_llm_integration.py` and the
browser review contract in `tests/add_stt.mjs`. Private evaluation recordings,
transcripts and benchmark diagnostics belong outside source and release archives.
