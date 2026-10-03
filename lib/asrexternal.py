# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy/paste review for all three ASR tasks. No endpoint or code execution."""
import io
import re
import tempfile
from pathlib import Path
import zipfile

import asrcorrection as correction
import asrworkspace
from llmconfig import LLMError
import promptkit

TASKS = ("suspect", "full", "workspace")
MAX_ANSWER = 128 * 1024
MAX_BUNDLE = 8 * 1024 * 1024
MAX_PROMPT = 64 * 1024


def batches(request, task, word_ids=None):
    if task not in TASKS:
        raise LLMError("bad-review", "Choose a transcript review method.")
    units = correction.sentence_units(request, 1200, "full" if task == "workspace" else task)
    if word_ids is not None:
        selected = set(word_ids)
        units = [dict(unit, targets=[w for w in unit["targets"] if w["word_id"] in selected]) for unit in units]
        units = [unit for unit in units if unit["targets"]]
    # Large collections of alternative hints must not turn one short caption
    # into an unbounded prompt. Each source target belongs to one batch.
    bounded = []
    for unit in units:
        targets, size = [], len(unit["text"].encode("utf-8"))
        for word in unit["targets"]:
            cost = len(correction.hint(word, 10).encode("utf-8")) if correction.suspect(word) else 0
            if targets and size + cost > 5000:
                bounded.append(dict(unit, targets=targets)); targets, size = [], len(unit["text"].encode("utf-8"))
            targets.append(word); size += cost
        if targets:
            bounded.append(dict(unit, targets=targets))
    out, window, size = [], [], 0
    for number, unit in enumerate(bounded):
        unit["sentence_id"] = "sentence%d" % number
        cost = len(unit["text"].encode("utf-8")) + sum(len(correction.hint(w, 10).encode("utf-8")) for w in unit["targets"] if correction.suspect(w))
        if window and (size + cost > 5000 or len(window) >= 12):
            out.append(window); window, size = [], 0
        window.append(unit); size += cost
    if window:
        out.append(window)
    return out


def ids(units):
    return {word["word_id"] for unit in units for word in unit["targets"]}


def workspace_files(request, units):
    transcript, suspects, words, captions, slots = asrworkspace._files(request)
    allowed = ids(units)
    region = {word["word_id"] for unit in units for word in unit["words"]}
    current_words = [dict(row) for row in words if row["word_id"] in region]
    current_captions, active = [], []
    # Keep inline evidence bounded even when a recognizer emits one enormous
    # caption. Helper offsets refer to these exact caption excerpts.
    for caption in captions:
        members = [row for row in current_words if row["segment_id"] == caption["segment_id"]]
        if not members:
            continue
        start = max(0, min(row["char_start"] for row in members) - 100)
        end = min(len(caption["text"]), max(row["char_end"] for row in members) + 100)
        text = caption["text"][start:end]
        current_captions.append(dict(caption, text=text))
        blanked = text
        for row in reversed(members):
            if row["slot"]:
                a, b = row["char_start"] - start, row["char_end"] - start
                blanked = blanked[:a] + "[" + row["slot"] + "]" + blanked[b:]
            row["char_start"] -= start; row["char_end"] -= start
        active.append(caption["segment_id"] + ": " + blanked)
    text = "\n".join(active)
    files = {"input/transcript.txt": transcript, "input/active.txt": text,
             "input/allowed.txt": " ".join(row["word_id"] for row in words if row["word_id"] in allowed),
             "input/suspects.csv": asrworkspace._csv([r for r in suspects if r["word_id"] in allowed],
                 ["slot", "word_id", "guess", "whisper_score", "low_asr_score", "dictionary_miss", "alternatives_available", "context", "whisper_hints"]),
             "input/words.csv": asrworkspace._csv(current_words,
                 ["word_id", "segment_id", "original", "slot", "char_start", "char_end"]),
             "input/captions.csv": asrworkspace._csv(current_captions, ["segment_id", "text"]),
             "input/skim.csv": asrworkspace._csv([], asrworkspace.FIELDS),
             "out/result.csv": asrworkspace._csv([], asrworkspace.FIELDS),
             "review.py": (Path(asrworkspace.__file__).parent / "asrskill" / asrworkspace.SKILL_NAME / "scripts/review.py").read_text(encoding="utf-8"),
             "SKILL.md": (Path(asrworkspace.__file__).parent / "asrskill" / asrworkspace.SKILL_NAME / "SKILL.md").read_text(encoding="utf-8")}
    if sum(len(value.encode("utf-8")) for value in files.values()) > MAX_BUNDLE:
        raise LLMError("too-large", "This text workspace exceeds the download limit. The sentence review methods remain available.")
    return files


def assembled(request, task, units):
    if task == "workspace":
        files = workspace_files(request, units)
        data = "\n\n".join(name + ":\n" + files[name] for name in ("input/active.txt", "input/allowed.txt", "input/words.csv", "input/suspects.csv", "input/captions.csv"))
    else:
        regions = []
        for unit in units:
            item = correction.messages(request, unit, task=task)[-1]["content"]
            regions.append("TARGET LABEL: " + unit["sentence_id"] + "\n" + item)
        data = "\n\n".join(regions)
    return promptkit.assemble("asr-" + task, request["language"], data=data)


def prompt(request, task, units):
    text = str(assembled(request, task, units))
    if len(text.encode("utf-8")) > MAX_PROMPT:
        raise LLMError("too-large", "This prompt exceeds its size limit. Review received suggestions and edit these words manually.")
    return text


def bundle(request, units, text):
    files = workspace_files(request, units)
    files["PROMPT.txt"] = text
    if sum(len(value.encode("utf-8")) for value in files.values()) > MAX_BUNDLE:
        raise LLMError("too-large", "The text workspace download exceeds its size limit.")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            entry = zipfile.ZipInfo("parseh-review/" + name)
            entry.external_attr = 0o100600 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content.encode("utf-8"))
    if stream.tell() > MAX_BUNDLE:
        raise LLMError("too-large", "The text workspace download exceeds its size limit.")
    return stream.getvalue()


def clean(answer):
    if (not isinstance(answer, str) or any(0xD800 <= ord(c) <= 0xDFFF for c in answer)
            or len(answer.encode("utf-8")) > MAX_ANSWER):
        raise LLMError("bad-external-answer", "Paste a bounded UTF-8 answer for this batch.")
    answer = answer.strip().replace("\r\n", "\n")
    if answer.startswith("```") and answer.endswith("```"):
        answer = "\n".join(answer.splitlines()[1:-1]).strip()
    if not answer:
        raise LLMError("bad-external-answer", "Paste the model's answer before importing it.")
    return answer


def parse(request, task, units, answer):
    answer = clean(answer)
    allowed = ids(units)
    proposals, failed, ignored = [], set(), []
    if task == "workspace":
        # Only parse the pasted CSV. Never execute a pasted response or its code.
        with tempfile.TemporaryDirectory(prefix="parseh-pasted-csv-") as folder:
            root = Path(folder); (root / "out").mkdir()
            (root / "out/result.csv").write_text(answer, encoding="utf-8")
            proposals, seen = asrworkspace._proposals(root, request, allowed)
        sources = correction.index(request)
        failed = {ident for ident in allowed - seen if correction.suspect(sources[ident])}
    else:
        expected = {unit["sentence_id"]: unit for unit in units}
        lines = {}
        for line in answer.splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r"(sentence[0-9]+):\s*(.*)", line)
            if not match or match[1] not in expected or match[1] in lines:
                raise LLMError("bad-external-answer", "Use each supplied sentence label once, followed by its complete sentence. Remove explanations and unknown labels.")
            lines[match[1]] = match[2]
        for ident, unit in expected.items():
            if ident not in lines:
                failed.update(word["word_id"] for word in unit["targets"])
                continue
            try:
                edits, extra = (correction.full_sentence_result if task == "full" else correction.sentence_result)(lines[ident], unit)
                ignored.extend(extra)
                for edit in edits:
                    if set(edit.get("word_ids", [edit["word_id"]])) <= allowed:
                        proposals.append(edit)
                    else:
                        ignored.append({"original": edit["original"], "replacement": edit["candidates"][0]["text"], "reason": "Outside the selected retry words."})
            except LLMError:
                failed.update(word["word_id"] for word in unit["targets"])
    proposed = {ident for proposal in proposals for ident in proposal.get("word_ids", [proposal["word_id"]])}
    return {"suggestions": proposals, "failed_word_ids": sorted(failed), "uncertain_word_ids": sorted(allowed - proposed),
            "reviewed_word_ids": sorted(allowed), "ignored_edits": ignored}
