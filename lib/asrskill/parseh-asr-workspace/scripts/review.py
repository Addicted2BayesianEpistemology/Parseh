# SPDX-License-Identifier: GPL-3.0-or-later
"""CSV boilerplate for the isolated agent. No linguistic decisions are made."""
import csv
from pathlib import Path


def read(name):
    with Path("input", name + ".csv").open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


words = {row["word_id"]: row for row in read("words")}
suspects = {row["word_id"]: row for row in read("suspects")}
captions = {row["segment_id"]: row["text"] for row in read("captions")}
allowed = Path("input/allowed.txt").read_text().split()


def show(offset=0, count=20):
    """Plain evidence, in source order. Large regions can be read in portions."""
    if type(offset) is not int or offset < 0 or type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Use offset >= 0 and count from 1 to 20.")
    print("Active text:")
    active = Path("input/active.txt").read_text(encoding="utf-8")
    print(active.encode("utf-8")[:1200].decode("utf-8", "ignore"))
    if len(active.encode("utf-8")) > 1200:
        print("Context clipped; the complete region is in input/active.txt.")
    print("Allowed words %d–%d of %d:" % (offset, min(offset + count, len(allowed)), len(allowed)))
    for ident in allowed[offset:offset + count]:
        word = words[ident]
        print(ident + " | " + word["original"])
        hint = suspects.get(ident)
        if hint:
            print("Blank " + hint["slot"] + " | " + hint["whisper_hints"])
            print("Context: " + hint["context"])
            if hint.get('heard_ipa') and hint.get('ipa_state') == 'complete':
                print('Estimated heard IPA around this word: ' + hint['heard_ipa'])
                print('Attribution: ' + hint.get('ipa_attribution', 'unspecified') +
                      '; may include neighboring sounds, not exact word alignment.')
                if hint.get('ipa_audio_start') and hint.get('ipa_audio_end'):
                    print('Original audio crop: ' + hint['ipa_audio_start'] + '–' + hint['ipa_audio_end'] + ' seconds.')
    skim = read("skim")
    if skim:
        print("Tentative first-pass edits in these captions:")
        for row in skim:
            if any(ident in words for ident in row["word_ids"].split()):
                print(row["original"] + " -> " + row["replacement"])


def save(rows):
    """rows = [(word_ids, replacement, reason), ...]; originals come from CSV."""
    with Path("out/result.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["word_ids", "original", "replacement", "reason"])
        for id_text, replacement, reason in rows:
            ids = id_text.split()
            if not ids or any(ident not in allowed for ident in ids):
                raise ValueError("Use only allowed word IDs.")
            members = [words[ident] for ident in ids]
            segment = members[0]["segment_id"]
            if any(word["segment_id"] != segment for word in members):
                raise ValueError("An edit cannot cross caption boundaries.")
            original = captions[segment][int(members[0]["char_start"]):int(members[-1]["char_end"])]
            writer.writerow([id_text, original, replacement, reason])
    print("Result CSV saved. Call finish_review when every required entry is present.")
