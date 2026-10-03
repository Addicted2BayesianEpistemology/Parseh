# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional N-best capability for the pinned faster-whisper worker only.

Return the native beam hypotheses, then map only unambiguous substitutions to
the selected hypothesis's words. Sequence log scores are NOT word probabilities.
No extra alignment, second recognizer, installed-runtime edits or server imports.
"""
import difflib
import math


def substitutions(original, candidate, spans, sequence_score):
    operations = difflib.SequenceMatcher(a=original, b=candidate, autojunk=False).get_opcodes()
    found = {}
    for key, start, end in spans:
        def belongs(a, b):
            if a != b:
                return a < end and b > start
            return (start < a < end or a == start and (start == 0 or original[start-1].isspace())
                    or a == end and (end == len(original) or original[end].isspace()))
        changes = [(a, b, c, d) for tag, a, b, c, d in operations
                   if tag != "equal" and belongs(a, b)]
        # Boundary insertions and edits touching two source words cannot be
        # attributed to this one word. Keep the source intact and omit them.
        if (not changes or any(a < start or b > end for a, b, _, _ in changes)
                or any(tag != "equal" and a == b and a in (start, end) and not belongs(a, b)
                       for tag, a, b, _, _ in operations)):
            continue
        replacement = original[start:end]
        for a, b, c, d in reversed(changes):
            replacement = replacement[:a-start] + candidate[c:d] + replacement[b-start:]
        if (not replacement.strip() or replacement == original[start:end]
                or len(replacement) > 400 or any(c.isspace() for c in replacement)):
            continue
        found[key] = {"text": replacement, "score": None,
                      "sequence_score": sequence_score, "score_kind": "sequence_log_score"}
    return found


def capable_model(WhisperModel, hypotheses=5):
    # Fake/older workers without these hooks retain their ordinary evidence.
    if not all(callable(getattr(WhisperModel, name, None)) for name in
               ("generate_with_fallback", "generate_segments", "add_word_timestamps")):
        return WhisperModel

    class BeamModel(WhisperModel):
        def generate_with_fallback(self, encoder_output, prompt, tokenizer, options):
            delegate = self.model

            class GenerateProxy:
                def __getattr__(self, name):
                    return getattr(delegate, name)

                def generate(self, *args, **kwargs):
                    # Beam width, patience, ranking and temperature stay native.
                    # Sampling fallbacks already request best_of hypotheses.
                    if kwargs.get("beam_size", 1) > 1:
                        native = dict(kwargs)
                        kwargs["num_hypotheses"] = min(hypotheses, kwargs["beam_size"])
                        try:
                            return delegate.generate(*args, **kwargs)
                        except TypeError:
                            return delegate.generate(*args, **native)
                    return delegate.generate(*args, **kwargs)

            self.model = GenerateProxy()
            try:
                result = super().generate_with_fallback(encoder_output, prompt, tokenizer, options)
            finally:
                self.model = delegate
            self._review_beam = (result[0], tokenizer)
            return result

        def add_word_timestamps(self, segments, *args, **kwargs):
            result = super().add_word_timestamps(segments, *args, **kwargs)
            self._review_words = {}
            try:
                generation, tokenizer = self._review_beam
                sequences = generation.sequences_ids[:hypotheses]
                if len(sequences) < 2:
                    return result
                original = tokenizer.decode(sequences[0])
                spans, cursor = [], 0
                for group in segments:
                    for segment in group:
                        for w in segment.get("words", []):
                            text = w["word"].strip()
                            at = original.find(text, cursor) if text else -1
                            if at < 0:
                                continue
                            cursor = at + len(text)
                            key = (w["start"], w["end"], w["word"])
                            spans.append((key, at, cursor))
                            self._review_words[key] = []
                for i, tokens in enumerate(sequences[1:], 1):
                    score = generation.scores[i] if i < len(generation.scores) else None
                    score = float(score) if isinstance(score, (int, float)) and math.isfinite(score) else None
                    edits = substitutions(original, tokenizer.decode(tokens), spans, score)
                    for key, candidate in edits.items():
                        if not any(c["text"] == candidate["text"] for c in self._review_words[key]):
                            self._review_words[key].append(candidate)
            except Exception:
                # Evidence extraction is optional; never invalidate native ASR.
                self._review_words = {}
            return result

        def generate_segments(self, *args, **kwargs):
            for segment in super().generate_segments(*args, **kwargs):
                for word in segment.words or []:
                    key = (word.start, word.end, word.word)
                    if key in getattr(self, "_review_words", {}):
                        # Word dataclasses are mutable. VAD remaps these same
                        # objects afterwards; evidence survives without touching
                        # text, probability or native timestamps.
                        word.alternatives = self._review_words[key]
                yield segment

    return BeamModel
