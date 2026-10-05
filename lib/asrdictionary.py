# SPDX-License-Identifier: GPL-3.0-or-later
"""Local dictionary evidence for a pending ASR review, using the readers' resolver.

Dictionary absence/failure and punctuation never mean an unknown word. A miss
is a review cue, not an assertion that a name or rare word is incorrect.
"""
from collections import OrderedDict
import threading
import unicodedata


def lexical(text):
    return any(unicodedata.category(c)[0] in "LN" for c in text)


def form(text):
    return "".join(c for c in unicodedata.normalize("NFC", text).casefold()
                   if unicodedata.category(c)[0] in "LNM")


class Resolver:
    def __init__(self, language):
        self.language = language
        self.cache = OrderedDict()
        self.lock = threading.RLock()

    def lookup(self, text):
        import lookup
        text = text[:400]
        with self.lock:
            if text in self.cache:
                self.cache.move_to_end(text)
                return self.cache[text]
        try:
            raw = lookup.look_up(self.language, text)
            if raw is None:
                result = {"state": "unavailable", "words": []}
            else:
                rows = []
                for row in raw["words"][:24]:
                    hits = [{"headword": str(h.get("headword", ""))[:200],
                             "pos": str(h.get("pos", ""))[:80],
                             "note": str(h.get("note", ""))[:200],
                             "senses": [str(s)[:300] for s in h.get("senses", [])[:3] if str(s).strip()]}
                            for h in row.get("hits", [])[:4]]
                    rows.append({"word": row["word"][:400], "hits": hits,
                                 "tried": [str(t)[:200] for t in row.get("tried", [])[:6]]})
                meaningful = [row for row in rows if lexical(row["word"])]
                state = ("not-word" if not lexical(text) else
                         "found" if meaningful and all(any(h["senses"] for h in r["hits"]) for r in meaningful)
                         else "missing")
                source = raw.get("source") or {}
                result = {"state": state, "words": rows,
                          "senses_language": source.get("senses_lang") or lookup.SENSES_LANG,
                          "source": str(source.get("source") or source.get("name") or "Installed dictionary")[:200]}
        except Exception:  # dictionary trouble must never discard ASR or model output
            result = {"state": "failed", "words": []}
        with self.lock:
            self.cache[text] = result
            if len(self.cache) > 2048:
                self.cache.popitem(last=False)
        return result

    def word(self, text, previous="", following=""):
        result = self.lookup(text)
        if result["state"] != "missing":
            return result
        # Reuse natural lookup's join_next rules (e.g. a separated Persian
        # negative prefix). Only a meaning for the complete joined form can
        # rescue a miss; a neighbour's own meaning cannot.
        for joined in (previous + " " + text if previous else "",
                       text + " " + following if following else ""):
            if not joined or len(joined) > 400:
                continue
            contextual = self.lookup(joined)
            rows = [r for r in contextual["words"] if form(r["word"]) == form(joined)
                    and any(h["senses"] for h in r["hits"])]
            if rows:
                return dict(contextual, state="found", words=rows, contextual=True)
        return result

    def enrich(self, evidence, cancelled=lambda: False):
        counts = {"found": 0, "missing": 0, "unavailable": 0, "failed": 0, "not-word": 0}
        for segment in evidence["segments"]:
            words = segment["words"]
            for i, word in enumerate(words):
                if cancelled():
                    return False
                result = self.word(word["text"], words[i-1]["text"] if i else "",
                                   words[i+1]["text"] if i+1 < len(words) else "")
                word["dictionary_state"] = result["state"]
                word["dictionary_miss"] = result["state"] == "missing"
                counts[result["state"]] += 1
        evidence["dictionary"] = dict(counts, language=self.language)
        return True
