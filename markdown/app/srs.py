"""srs — the exercise decks' scheduler: Anki's SM-2 (v2/v3) without a database.

Pure and stdlib-only.  A card's schedule is a small dict (new_state());
answer() returns the next one, preview() shows what each rating would do,
queue() picks what to study now.  Nothing here reads the clock: every
function takes `now`, a timezone-aware datetime (the server passes
datetime.now().astimezone(), since the learner's machine is the server).

A "day" is the learner's LOCAL calendar day starting at rollover_hour
(04:00 as in Anki), so an answer given at 01:00 still belongs to the
evening before.  A review's due is day_start(): the rollover hour, with the
offset in force when the card was answered.  due_day() takes that due's day
from its own calendar date, so a card scheduled in summer time is not due
the evening before once the clocks go back (04:00+02:00 is 03:00+01:00).
Any other stored time is converted to now's timezone before its day is
taken.

State:  {"state": new|learning|review|relearning, "due": iso|None,
         "step": index into the current step list, "interval": days (for
         relearning: the interval the card returns to), "ease": float|None
         (None until graduated), "reps", "lapses", "last_review": iso|None}

Where this is not Anki:
- fuzz is a hash of (seed, rating, reps before the answer), not random, so
  preview() shows exactly the interval answer() will give;
- halves round up (Anki rounds f32 away from zero; Python's round() would
  round 2.5 to 2);
- minimum_interval clamps every day interval, not only a lapse's;
- a preview label for a day interval reads the interval ("1d"), not the
  hours left until the next day's rollover.
"""
import hashlib
import math
from datetime import date, datetime, time, timedelta, timezone

DEFAULTS = {
    "new_per_day": 20, "reviews_per_day": 200,
    "learning_steps": [1.0, 10.0],     # minutes
    "relearning_steps": [10.0],        # minutes
    "graduating_interval": 1,          # days
    "easy_interval": 4,                # days
    "starting_ease": 2.5, "minimum_ease": 1.3,
    "easy_bonus": 1.3, "hard_multiplier": 1.2, "interval_modifier": 1.0,
    "new_interval": 0.0,               # fraction of the old interval kept after a lapse
    "minimum_interval": 1, "maximum_interval": 36500,
    "rollover_hour": 4,                # a "day" starts at 04:00 local, as in Anki
    "learn_ahead_minutes": 20,
}
RATINGS = ("again", "hard", "good", "easy")
STATES = ("new", "learning", "review", "relearning")

MAX_DAYS = 36500                       # a hundred years: keeps every due inside datetime's range
MAX_STEPS = 50
MAX_STEP_MINUTES = MAX_DAYS * 1440
# A stored ease above this reads as none (starting_ease): interval * ease *
# every multiplier at its highest stays finite, and study only adds 0.15 per
# Easy, so no real deck gets near it.
MAX_EASE = 1e6
DAY = 86400
_MONTH = DAY * 365 / 12
_YEAR = DAY * 365

# Whole-number options: (lowest, highest).
_WHOLE = {
    "new_per_day": (0, 9999), "reviews_per_day": (0, 9999),
    "graduating_interval": (1, MAX_DAYS), "easy_interval": (1, MAX_DAYS),
    "minimum_interval": (1, MAX_DAYS), "maximum_interval": (1, MAX_DAYS),
    "rollover_hour": (0, 23), "learn_ahead_minutes": (0, 1440),
}
# Real-number options: (lowest, highest).  An ease below 1 would shrink an
# interval on "good"; the upper bounds only keep the arithmetic finite.
_REAL = {
    "starting_ease": (1.0, 10.0), "minimum_ease": (1.0, 10.0),
    "easy_bonus": (1.0, 10.0), "hard_multiplier": (0.0, 10.0),
    "interval_modifier": (0.01, 10.0), "new_interval": (0.0, 1.0),
}
_STEPS = ("learning_steps", "relearning_steps")


class SettingsError(ValueError):
    """A deck option that cannot be used; the message names the field."""


# ---------------------------------------------------------------- settings

def settings(raw=None):
    """DEFAULTS overlaid with raw's known keys, checked; unknown keys dropped."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise SettingsError("settings must be an object of named options")
    out = {k: list(v) if isinstance(v, list) else v for k, v in DEFAULTS.items()}
    for key in DEFAULTS:
        if key not in raw:
            continue
        value = raw[key]
        if key in _STEPS:
            out[key] = _steps(key, value)
        elif key in _WHOLE:
            out[key] = _whole(key, value, *_WHOLE[key])
        else:
            out[key] = _real(key, value, *_REAL[key])
    if out["starting_ease"] < out["minimum_ease"]:
        raise SettingsError("starting_ease must not be below minimum_ease")
    if out["maximum_interval"] < out["minimum_interval"]:
        raise SettingsError("maximum_interval must not be below minimum_interval")
    return out


def _is_number(value):
    # bool is an int subclass: True must not pass for 1.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _whole(key, value, low, high):
    problem = SettingsError(f"{key} must be a whole number from {low} to {high}")
    if not _is_number(value):
        raise problem
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise problem
        value = int(value)
    if not low <= value <= high:
        raise problem
    return value


def _real(key, value, low, high):
    problem = SettingsError(f"{key} must be a number from {low:g} to {high:g}")
    # The comparison also refuses nan and the infinities.
    if not _is_number(value) or not low <= value <= high:
        raise problem
    return float(value)


def _steps(key, value):
    problem = SettingsError(f"{key} must be a list of at most {MAX_STEPS} steps, "
                            "each a positive number of minutes")
    if not isinstance(value, (list, tuple)) or len(value) > MAX_STEPS:
        raise problem
    for step in value:
        if not _is_number(step) or not 0 < step <= MAX_STEP_MINUTES:
            raise problem
    return [float(step) for step in value]


def _conf(cfg):
    # Callers normally pass settings() output; a partial or missing one is
    # completed (and checked) here.
    if isinstance(cfg, dict) and all(k in cfg for k in DEFAULTS):
        return cfg
    return settings(cfg)


# ---------------------------------------------------------------- days and times

def _hour(cfg):
    if isinstance(cfg, dict) and "rollover_hour" in cfg:
        return cfg["rollover_hour"]
    return DEFAULTS["rollover_hour"]


def day_number(dt, cfg):
    """The local calendar day (an ordinal) of dt - rollover_hour hours.

    The day is read off dt's own wall clock: a stored due's day is due_day()."""
    return (dt.replace(tzinfo=None) - timedelta(hours=_hour(cfg))).date().toordinal()


def day_start(day, tzinfo, cfg):
    """The moment `day` (an ordinal) begins: rollover_hour, local."""
    return datetime.combine(date.fromordinal(day), time(_hour(cfg)), tzinfo=tzinfo)


def _checked(dt):
    # This module never writes a naive time; one from elsewhere is read as
    # the machine's local time.  A moment outside years 2..9998 (UTC) is
    # refused: converting it to another offset, or taking the rollover hours
    # off it, would leave datetime's range and raise.
    try:
        if dt.tzinfo is None or dt.utcoffset() is None:
            dt = dt.astimezone()
        year = dt.astimezone(timezone.utc).year
    except (OverflowError, ValueError, OSError):
        return None
    return dt if 2 <= year <= 9998 else None


def _parse(text):
    if not isinstance(text, str) or not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _checked(dt)


def due_at(state):
    """The state's due as an aware datetime, or None (new, or unreadable)."""
    return _parse(state.get("due")) if isinstance(state, dict) else None


def due_day(due, now, cfg):
    """The day (an ordinal, as day_number) a review due, ISO text or datetime, belongs to.

    A due at exactly the rollover hour on its own clock is what day_start
    wrote: its own calendar date is the day it was scheduled for, whatever
    offset `now` has.  Any other due is an instant, converted to now's
    timezone first.  A due that cannot be read is today (due now)."""
    _aware(now)
    moment = _checked(due) if isinstance(due, datetime) else _parse(due)
    return _due_day(moment or now, now, cfg)


def _due_day(due, now, cfg):
    # time() drops the offset and keeps the microseconds: day_start writes none
    if due.time() == time(_hour(cfg)):
        return day_number(due, cfg)
    return day_number(_local(due, now), cfg)


def _aware(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")


def _local(dt, now):
    return dt.astimezone(now.tzinfo)


def _utc(dt):
    # Aware datetimes sharing one tzinfo object subtract and compare by wall
    # clock; in UTC they compare by elapsed time.
    return dt.astimezone(timezone.utc)


def _after_minutes(now, minutes):
    # Elapsed time, not wall-clock arithmetic: a step across a DST change
    # still lasts its minutes.
    return (_utc(now) + timedelta(minutes=minutes)).astimezone(now.tzinfo)


def _round(x):
    # int(inf) raises: a runaway product saturates instead (every day
    # interval is clamped after rounding).
    if isinstance(x, float) and not math.isfinite(x):
        return MAX_DAYS if x > 0 else 0
    return int(math.floor(x + 0.5))


# ---------------------------------------------------------------- labels

def _tenths(x):
    n = math.floor(x * 10 + 0.5) / 10
    return str(int(n)) if n == int(n) else f"{n:.1f}"


def label(seconds):
    """A button label for a span: "<1m" "6m" "1h" "5h" "1d" "12d" "1.5mo" "2.1y"."""
    s = max(0, seconds)
    if s < 60:
        return "<1m"
    if s < 3600:
        n = _round(s / 60)
        return "1h" if n >= 60 else f"{n}m"
    if s < DAY:
        n = _round(s / 3600)
        return "1d" if n >= 24 else f"{n}h"
    if s < _MONTH:
        return f"{_round(s / DAY)}d"
    if s < _YEAR:
        months = math.floor(s / _MONTH * 10 + 0.5) / 10
        return "1y" if months >= 12 else f"{_tenths(months)}mo"
    return f"{_tenths(s / _YEAR)}y"


# ---------------------------------------------------------------- answering

def new_state():
    return {"state": "new", "due": None, "step": 0, "interval": 0, "ease": None,
            "reps": 0, "lapses": 0, "last_review": None}


def _count(value, high=None):
    if isinstance(value, float) and math.isfinite(value):
        value = int(value)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return 0
    return min(value, high) if high is not None else value


def _normal(state):
    """A clean copy of a stored state: unknown names read as new, odd values as defaults."""
    card = new_state()
    if not isinstance(state, dict):
        return card
    card["state"] = state.get("state") if state.get("state") in STATES else "new"
    card["step"] = _count(state.get("step"))
    card["interval"] = _count(state.get("interval"), MAX_DAYS)
    ease = state.get("ease")
    # Compared before float(): an integer too large for a float must not
    # raise, and nan and the infinities fail the comparison.
    if _is_number(ease) and 0 < ease <= MAX_EASE:
        card["ease"] = float(ease)
    card["reps"] = _count(state.get("reps"))
    card["lapses"] = _count(state.get("lapses"))
    for key in ("due", "last_review"):
        if isinstance(state.get(key), str):
            card[key] = state[key]
    return card


def _clamp(ivl, cfg):
    return max(cfg["minimum_interval"], min(cfg["maximum_interval"], ivl))


def _fuzz(ivl, rating, reps_before, seed, cfg):
    """Spread day intervals of 3 or more a little, the same way every time."""
    if ivl < 3:
        return ivl
    digest = hashlib.sha1(f"{seed}:{rating}:{reps_before}".encode("utf-8")).hexdigest()
    frac = int(digest[:8], 16) / 2 ** 32
    pct = 0.15 if ivl <= 7 else 0.10 if ivl <= 20 else 0.05
    delta = max(1, _round(ivl * pct))
    return _clamp(ivl - delta + _round(frac * 2 * delta), cfg)


def _hard_delay(steps, step):
    if step == 0 and len(steps) >= 2:
        return (steps[0] + steps[1]) / 2
    if step == 0:
        return min(steps[0] * 1.5, steps[0] + 1440)
    return steps[step]


def _ease(value):
    # 2.3 - 0.2 is 2.0999999999999996 in binary; keep the stored ease tidy.
    return round(value, 4)


def _to_review(out, ivl, ease, today, now, cfg):
    out.update(state="review", step=0, interval=ivl, ease=_ease(ease),
               due=day_start(today + ivl, now.tzinfo, cfg).isoformat())
    return out


def _review_intervals(card, ease, today, now, reps_before, seed, cfg):
    """hard, good and easy for a review card, fuzzed and kept in that order."""
    ivl = card["interval"]
    due = due_at(card)
    late = max(0, today - _due_day(due, now, cfg)) if due else 0
    modifier = cfg["interval_modifier"]
    hard = ivl * cfg["hard_multiplier"] * modifier
    if cfg["hard_multiplier"] > 1:
        hard = max(hard, ivl + 1)
    hard = _clamp(_round(hard), cfg)
    good = _clamp(max(_round((ivl + late / 2) * ease * modifier), hard + 1), cfg)
    easy = _clamp(max(_round((ivl + late) * ease * modifier * cfg["easy_bonus"]), good + 1), cfg)
    hard = _fuzz(hard, "hard", reps_before, seed, cfg)
    good = _fuzz(good, "good", reps_before, seed, cfg)
    easy = _fuzz(easy, "easy", reps_before, seed, cfg)
    top = cfg["maximum_interval"]
    if cfg["hard_multiplier"] > 1:
        # the I + 1 floor holds after fuzz too (Anki fuzzes inside it)
        hard = min(max(hard, ivl + 1), top)
    good = min(max(good, hard + 1), top)
    easy = min(max(easy, good + 1), top)
    return {"hard": hard, "good": good, "easy": easy}


def _answer(card, rating, now, cfg, seed):
    reps_before = card["reps"]
    out = dict(card, reps=reps_before + 1, last_review=now.isoformat())
    today = day_number(now, cfg)
    name = card["state"]
    starting = cfg["starting_ease"]

    if name in ("new", "learning"):
        steps = cfg["learning_steps"]
        step = 0 if name == "new" else min(card["step"], max(len(steps) - 1, 0))
        if not steps or rating == "easy" or (rating == "good" and step + 1 >= len(steps)):
            ivl = cfg["easy_interval"] if rating == "easy" else cfg["graduating_interval"]
            ivl = _fuzz(_clamp(ivl, cfg), rating, reps_before, seed, cfg)
            if (rating == "easy" and (not steps or step + 1 >= len(steps))
                    and cfg["easy_interval"] >= cfg["graduating_interval"]):
                # Good graduates this card too: after fuzz Easy stays at
                # least a day longer, as a review card's answers are kept
                # (equal options included, else Easy is shorter a third of the time)
                good = _fuzz(_clamp(cfg["graduating_interval"], cfg), "good",
                             reps_before, seed, cfg)
                ivl = min(max(ivl, good + 1), cfg["maximum_interval"])
            return _to_review(out, ivl, starting, today, now, cfg)
        if rating == "again":
            step, delay = 0, steps[0]
        elif rating == "hard":
            delay = _hard_delay(steps, step)
        else:
            step += 1
            delay = steps[step]
        out.update(state="learning", step=step, interval=0, ease=None,
                   due=_after_minutes(now, delay).isoformat())
        return out

    ease = card["ease"] if card["ease"] is not None else starting

    if name == "review":
        if rating == "again":
            out["lapses"] = card["lapses"] + 1
            ease = max(cfg["minimum_ease"], ease - 0.20)
            lapse = _clamp(max(cfg["minimum_interval"],
                               _round(card["interval"] * cfg["new_interval"])), cfg)
            relearn = cfg["relearning_steps"]
            if relearn:
                out.update(state="relearning", step=0, interval=lapse, ease=_ease(ease),
                           due=_after_minutes(now, relearn[0]).isoformat())
                return out
            lapse = _fuzz(lapse, rating, reps_before, seed, cfg)
            return _to_review(out, lapse, ease, today, now, cfg)
        ivl = _review_intervals(card, ease, today, now, reps_before, seed, cfg)[rating]
        if rating == "hard":
            ease = max(cfg["minimum_ease"], ease - 0.15)
        elif rating == "easy":
            ease += 0.15
        return _to_review(out, ivl, ease, today, now, cfg)

    # relearning: the card returns to its stored interval when the steps are done
    steps = cfg["relearning_steps"]
    step = min(card["step"], max(len(steps) - 1, 0))
    back = card["interval"]
    if rating == "easy":
        ivl = _fuzz(_clamp(back + 1, cfg), rating, reps_before, seed, cfg)
        if not steps or step + 1 >= len(steps):
            # Good ends the steps too: after fuzz Easy stays the longer
            good = _fuzz(_clamp(back, cfg), "good", reps_before, seed, cfg)
            ivl = min(max(ivl, good + 1), cfg["maximum_interval"])
        return _to_review(out, ivl, ease, today, now, cfg)
    if not steps or (rating == "good" and step + 1 >= len(steps)):
        ivl = _fuzz(_clamp(back, cfg), rating, reps_before, seed, cfg)
        return _to_review(out, ivl, ease, today, now, cfg)
    if rating == "again":
        step, delay = 0, steps[0]
    elif rating == "hard":
        delay = _hard_delay(steps, step)
    else:
        step += 1
        delay = steps[step]
    out.update(state="relearning", step=step, ease=_ease(ease),
               due=_after_minutes(now, delay).isoformat())
    return out


def answer(state, rating, now, cfg, seed=""):
    """The state after rating the card at `now` (a new dict; `state` is not touched)."""
    if rating not in RATINGS:
        raise ValueError(f"unknown rating {rating!r} (expected one of {', '.join(RATINGS)})")
    _aware(now)
    return _answer(_normal(state), rating, now, _conf(cfg), str(seed))


def preview(state, now, cfg, seed=""):
    """{rating: {"due", "seconds", "label"}}: exactly what answer() would schedule."""
    _aware(now)
    cfg, card, seed = _conf(cfg), _normal(state), str(seed)
    shown = {}
    for rating in RATINGS:
        after = _answer(card, rating, now, cfg, seed)
        due = datetime.fromisoformat(after["due"])
        # timedelta arithmetic is exact; float timestamps can lose a second.
        seconds = max(0, (_utc(due) - _utc(now)) // timedelta(seconds=1))
        span = after["interval"] * DAY if after["state"] == "review" else seconds
        shown[rating] = {"due": after["due"], "seconds": seconds, "label": label(span)}
    return shown


# ---------------------------------------------------------------- what to study

def _created_key(created):
    moment = _parse(created)
    return (0, _utc(moment)) if moment else (1, None)


def queue(entries, now, cfg, done_today=None):
    """What to study next: {"next": item_id|None, "counts": {...}, "next_due": iso|None}.

    entries: (item_id, created_iso, state) triples; done_today: the answers
    already given today, {"new": n, "review": n} (today_counts())."""
    _aware(now)
    cfg = _conf(cfg)
    done = done_today if isinstance(done_today, dict) else {}
    today = day_number(now, cfg)
    stamp = _utc(now)
    ahead = stamp + timedelta(minutes=cfg["learn_ahead_minutes"])
    learning, reviews, new, later = [], [], [], []
    for item_id, created, state in entries:
        card = _normal(state)
        born = _created_key(created)
        if card["state"] == "new":
            new.append((born, str(item_id), item_id))
            continue
        # A due that cannot be read must not hide the card: it is due now.
        due = due_at(card) or now
        when = _utc(due)
        if card["state"] in ("learning", "relearning"):
            if when <= ahead:
                learning.append((when, born, str(item_id), item_id))
            else:
                later.append(due)
            continue
        day = _due_day(due, now, cfg)
        if day <= today:
            reviews.append((when, born, str(item_id), item_id))
        else:
            # it is counted from the start of its day, whatever its stored time
            later.append(day_start(day, now.tzinfo, cfg))
    learning.sort()
    reviews.sort()
    new.sort()

    review_room = max(0, cfg["reviews_per_day"] - _count(done.get("review")))
    new_room = max(0, cfg["new_per_day"] - _count(done.get("new")))
    # Cards held back only by today's limit come back when the next day starts
    # (unless the limit is zero, which holds them back every day).
    tomorrow = day_start(today + 1, now.tzinfo, cfg)
    if len(reviews) > review_room and cfg["reviews_per_day"] > 0:
        later.append(tomorrow)
    if len(new) > new_room and cfg["new_per_day"] > 0:
        later.append(tomorrow)
    reviews = reviews[:review_room]
    new = new[:new_room]

    if learning and learning[0][0] <= stamp:
        nxt = learning[0][-1]
    elif reviews:
        nxt = reviews[0][-1]
    elif new:
        nxt = new[0][-1]
    elif learning:
        nxt = learning[0][-1]          # learn ahead: nothing else is left today
    else:
        nxt = None
    soonest = min(later, key=_utc) if later else None
    return {"next": nxt,
            "counts": {"new": len(new), "learning": len(learning), "review": len(reviews)},
            "next_due": _local(soonest, now).isoformat() if soonest else None}


def today_counts(histories, now, cfg):
    """How many new cards and reviews were answered today, from schedule histories."""
    _aware(now)
    today = day_number(now, cfg)
    counts = {"new": 0, "review": 0}
    for history in histories or ():
        if not isinstance(history, list):
            continue
        for entry in history:
            if not isinstance(entry, dict) or entry.get("before") not in counts:
                continue
            at = _parse(entry.get("at"))
            if at is not None and day_number(_local(at, now), cfg) == today:
                counts[entry["before"]] += 1
    return counts
