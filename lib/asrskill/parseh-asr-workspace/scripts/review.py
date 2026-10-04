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
target_file = Path("input/targets.txt")
targets = target_file.read_text().split() if target_file.exists() else allowed


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
        print(ident + " | " + word["original"] + (" | phase target" if ident in targets else " | adjacent context"))
        hint = suspects.get(ident)
        if hint:
            print("Blank " + hint["slot"] + " | " + hint["whisper_hints"])
            print("Context: " + hint["context"])
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
            if (not ids or len(ids) > 8 or len(set(ids)) != len(ids)
                    or any(ident not in allowed for ident in ids) or not set(ids).intersection(targets)):
                raise ValueError("Use up to eight editable word IDs including a phase target.")
            members = [words[ident] for ident in ids]
            segment = members[0]["segment_id"]
            if any(word["segment_id"] != segment for word in members):
                raise ValueError("An edit cannot cross caption boundaries.")
            ordered = [ident for ident, word in words.items() if word['segment_id'] == segment]
            first = ordered.index(ids[0])
            if ordered[first:first + len(ids)] != ids:
                raise ValueError("Use consecutive word IDs in source order.")
            original = captions[segment][int(members[0]["char_start"]):int(members[-1]["char_end"])]
            writer.writerow([id_text, original, replacement, reason])
    print("Result CSV saved. Call finish_review when every required entry is present.")
