# LLM connection and correction review

`llmconfig.py` owns the versioned host-only `config/llm.json` configuration.
Missing, malformed and unknown-version configurations load as unconfigured.
`settingspage.py` classifies `llm.connection` as risky and gates every save,
reset, discovery, connection test and link-import route before it runs.
Credentials are masked, explicitly kept/replaced/cleared, stored with mode
0600 and excluded from source, release manifests and prefs. Status never
returns the saved key or its fingerprint. An opaque session connection ID
ties the destination shown before review to the saved connection; changing
settings requires another deliberate choice before text is sent. The last
connection test is session-local.

`llmadapter.py` is the reusable boundary for models, connection testing and
structured text generation. Ollama, Unsloth and generic configuration select
the same OpenAI-compatible implementation. No inference library or SDK is
added to the main environment. HTTP does not follow redirects or proxy
environment settings. A wall-clock deadline, cancellation event and socket
shutdown bound the request. Error messages contain sanitized categories and
HTTP status, never response bodies, prompts or credentials. Known unloaded-model
errors produce a static instruction to load the model in the endpoint's own
interface; Parseh neither loads it nor retries that error without JSON mode.
JSON-mode output
is still parsed and validated. A connection test can record an unsupported
JSON mode while retaining structured JSON parsing for feature calls.

`asrcorrection.py` owns the feature prompt and CorrectionRequest /
CorrectionResult contract. ASR evidence receives stable segment/word IDs and
exact Unicode code-point spans in the original panel. Unmatched spans are
inspectable but ineligible for edits. Word scores stay nullable. The worker
keeps `asr_words` before CTC alignment so CTC probabilities cannot replace
Whisper evidence. `word_alternatives` is the capability hook for genuine
backend alternatives; pinned faster-whisper currently returns unavailable.

Windows own disjoint target IDs with bounded overlapping context. Input
budgeting counts UTF-8 bytes conservatively, reserving instructions and
output tokens against the host-configured context length. Candidate IDs,
original spans, scores, evidence echoes, reasons, duplicates and response
size are validated. Unknown fields and schemas are rejected. Optional
`assessment` and `uncertain_word_ids` distinguish no likely error from
uncertainty. All windows must validate before any suggestions are exposed.

Jobs retain the existing token, ASR panel and held-data fields and add
`review: {evidence, choice, correction, result}`. ASR ends in
`awaiting-review-choice`, after releasing the model/runtime hold. Pending
reviews do not hold the execution slot. `review {job, mode, source_sha256, connection_id}`
either opens Whisper-only review or claims the single slot for `correcting`.
Saved endpoint/model settings are snapshotted and checked before each window
and publication. Changes invalidate in-flight suggestions. `cancel-review`
or Cancel during correction aborts outstanding HTTP work and restores the
review choice with no accepted/partial suggestions. Per-request timeout and
failure release the slot without turning successful ASR into a failure.

`use {job, source_sha256, decisions}` accepts only candidate indices keyed by
validated word IDs. It applies replacements to exact panel spans, checks
caption clocks/boundaries against the original and returns the reviewed
panel. The immutable Whisper panel/evidence remain intact. The existing word
tape sync retires changed atoms and estimates replacements. The returned
timing notice directs the person to the existing editor; retained audio is
not available for re-alignment. Caption clocks are never inferred anew.

`asrreview.js` handles browser draft decisions and Unicode-safe preview;
`addstt.js` owns source/language/model/transcript ties, polling and the only
explicit Use handoff. The browser requests no generation on ASR completion
or from a remembered default. Dynamic endpoint/model/source text is rendered
with textContent. Details use focus, hover and click/tap with glyphs plus
border cues. Mobile-specific code and paths are unchanged.

New regression coverage is in `tests/test_llm_integration.py`; the existing
fake-worker helpers explicitly choose Whisper review when their callers ask
for a completed job. Tests require no external model, GPU or endpoint.
Loopback HTTP is supplied by an in-process fake server. For this change the
user requested a release rehearsal without executing test suites.
