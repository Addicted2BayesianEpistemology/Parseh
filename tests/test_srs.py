# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import hashlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "markdown" / "app"))

import srs

# Fixed, non-UTC offsets: a scheduler that takes the day from UTC (or from a
# naive datetime) gets these wrong.
TEHRAN = timezone(timedelta(hours=3, minutes=30))
NEW_YORK = timezone(timedelta(hours=-5))
# What datetime.now().astimezone() gives in Rome before and after the clocks
# go back (25 Oct 2026): a fixed offset each, never a zone that knows both.
CEST = timezone(timedelta(hours=2))
CET = timezone(timedelta(hours=1))
CFG = srs.settings()


def at(y, mo, d, h=0, mi=0, s=0, tz=TEHRAN):
    return datetime(y, mo, d, h, mi, s, tzinfo=tz)


NOW = at(2026, 9, 14, 15, 0)          # an afternoon: well after the 04:00 rollover
TODAY = NOW.date().toordinal()


def fuzz_frac(seed, rating, reps):
    digest = hashlib.sha1(f"{seed}:{rating}:{reps}".encode()).hexdigest()
    return int(digest[:8], 16) / 2 ** 32


def neutral_seed(reps, ratings=("hard", "good", "easy")):
    """A seed whose fuzz leaves every interval up to 100 days unchanged."""
    for n in range(100000):
        seed = f"n{n}"
        if all(0.45 <= fuzz_frac(seed, r, reps) < 0.55 for r in ratings):
            return seed
    raise AssertionError("no neutral seed")


def review_card(interval=10, ease=2.5, due=None, reps=5, lapses=0):
    due = due or srs.day_start(TODAY, TEHRAN, CFG)
    return {"state": "review", "due": due.isoformat(), "step": 0, "interval": interval,
            "ease": ease, "reps": reps, "lapses": lapses, "last_review": None}


def learning_card(step=0, reps=1):
    return {"state": "learning", "due": NOW.isoformat(), "step": step, "interval": 0,
            "ease": None, "reps": reps, "lapses": 0, "last_review": None}


def relearning_card(step=0, interval=1, ease=2.3, reps=6):
    return {"state": "relearning", "due": NOW.isoformat(), "step": step, "interval": interval,
            "ease": ease, "reps": reps, "lapses": 1, "last_review": None}


def cfg(**changes):
    return srs.settings(changes)


class SettingsTests(unittest.TestCase):
    def test_defaults_are_a_copy(self):
        self.assertEqual(srs.DEFAULTS, srs.settings())
        self.assertEqual(srs.DEFAULTS, srs.settings({}))
        got = srs.settings()
        got["learning_steps"].append(99.0)
        self.assertEqual([1.0, 10.0], srs.DEFAULTS["learning_steps"])

    def test_known_keys_overlay_unknown_dropped(self):
        got = srs.settings({"new_per_day": 5, "learning_steps": [2, 20], "bogus": 1})
        self.assertEqual(5, got["new_per_day"])
        self.assertEqual([2.0, 20.0], got["learning_steps"])
        self.assertNotIn("bogus", got)
        self.assertEqual(set(srs.DEFAULTS), set(got))

    def test_types_normalised(self):
        got = srs.settings({"new_per_day": 20.0, "starting_ease": 3, "relearning_steps": []})
        self.assertIs(type(got["new_per_day"]), int)
        self.assertIs(type(got["starting_ease"]), float)
        self.assertEqual([], got["relearning_steps"])
        self.assertEqual([], srs.settings({"learning_steps": []})["learning_steps"])

    def test_refusals_name_the_field(self):
        bad = [
            ("new_per_day", -1), ("new_per_day", "20"), ("new_per_day", True),
            ("new_per_day", None), ("new_per_day", 1.5), ("new_per_day", 10000),
            ("reviews_per_day", 10000), ("reviews_per_day", float("nan")),
            ("graduating_interval", 0), ("easy_interval", -4),
            ("minimum_interval", 0), ("maximum_interval", 36501),
            ("rollover_hour", 24), ("rollover_hour", -1), ("rollover_hour", False),
            ("learn_ahead_minutes", -5),
            ("starting_ease", True), ("starting_ease", "2.5"), ("starting_ease", float("inf")),
            ("minimum_ease", -1.3), ("minimum_ease", 0.5), ("easy_bonus", 0.9),
            ("hard_multiplier", -1), ("interval_modifier", 0), ("new_interval", 1.5),
            ("new_interval", -0.1),
            ("learning_steps", "1 10"), ("learning_steps", [1, 0]), ("learning_steps", [-1]),
            ("learning_steps", [True]), ("learning_steps", ["1"]), ("learning_steps", None),
            ("learning_steps", [float("nan")]), ("relearning_steps", 10),
            ("relearning_steps", [1] * 51),
        ]
        for key, value in bad:
            with self.subTest(key=key, value=value):
                with self.assertRaises(srs.SettingsError) as caught:
                    srs.settings({key: value})
                self.assertIn(key, str(caught.exception))

    def test_cross_field_refusals(self):
        with self.assertRaisesRegex(srs.SettingsError, "starting_ease"):
            srs.settings({"starting_ease": 1.5, "minimum_ease": 2.0})
        with self.assertRaisesRegex(srs.SettingsError, "maximum_interval"):
            srs.settings({"minimum_interval": 10, "maximum_interval": 5})

    def test_not_an_object(self):
        self.assertTrue(issubclass(srs.SettingsError, ValueError))
        with self.assertRaises(srs.SettingsError):
            srs.settings(["new_per_day", 5])

    def test_partial_cfg_is_completed_by_the_scheduler(self):
        got = srs.answer(srs.new_state(), "good", NOW, {"learning_steps": [3]}, seed="x")
        self.assertEqual("review", got["state"])
        got = srs.answer(srs.new_state(), "again", NOW, None)
        self.assertEqual((NOW + timedelta(minutes=1)).isoformat(), got["due"])


class LabelTests(unittest.TestCase):
    def test_labels(self):
        day = 86400
        cases = [
            (-5, "<1m"), (0, "<1m"), (59, "<1m"), (60, "1m"), (89, "1m"), (330, "6m"),
            (600, "10m"), (3599, "1h"), (3600, "1h"), (5 * 3600, "5h"), (86399, "1d"),
            (day, "1d"), (12 * day, "12d"), (30 * day, "30d"), (31 * day, "1mo"),
            (45 * day, "1.5mo"), (364 * day, "1y"), (365 * day, "1y"), (766 * day, "2.1y"),
            (3650 * day, "10y"),
        ]
        for seconds, text in cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(text, srs.label(seconds))


class DayTests(unittest.TestCase):
    def test_rollover_boundary_local(self):
        before = at(2026, 9, 15, 3, 59, 59)
        after = at(2026, 9, 15, 4, 0, 0)
        self.assertEqual(at(2026, 9, 14).date().toordinal(), srs.day_number(before, CFG))
        self.assertEqual(at(2026, 9, 15).date().toordinal(), srs.day_number(after, CFG))

    def test_day_is_local_not_utc(self):
        # 23:30 in New York is 04:30 UTC the next day: past a UTC rollover,
        # but still the 14th locally.
        evening = at(2026, 9, 14, 23, 30, tz=NEW_YORK)
        self.assertEqual(TODAY, srs.day_number(evening, CFG))
        # 02:00 in Tehran is 22:30 UTC the day before; locally it is before
        # the rollover, so also the 14th.
        night = at(2026, 9, 15, 2, 0)
        self.assertEqual(TODAY, srs.day_number(night, CFG))

    def test_day_start_round_trip(self):
        start = srs.day_start(TODAY + 1, TEHRAN, CFG)
        self.assertEqual(at(2026, 9, 15, 4, 0), start)
        self.assertEqual("2026-09-15T04:00:00+03:30", start.isoformat())
        self.assertEqual(TODAY + 1, srs.day_number(start, CFG))
        midnight = cfg(rollover_hour=0)
        self.assertEqual(at(2026, 9, 15, 0, 0), srs.day_start(TODAY + 1, TEHRAN, midnight))
        self.assertEqual(TODAY + 1, srs.day_number(at(2026, 9, 15, 0, 30), midnight))

    def test_due_at(self):
        self.assertIsNone(srs.due_at(srs.new_state()))
        self.assertIsNone(srs.due_at({"due": "not a date"}))
        self.assertEqual(NOW, srs.due_at({"due": NOW.isoformat()}))
        self.assertEqual(NOW, srs.due_at({"due": "2026-09-14T11:30:00Z"}))


class LearningTests(unittest.TestCase):
    def test_new_state(self):
        self.assertEqual({"state": "new", "due": None, "step": 0, "interval": 0, "ease": None,
                          "reps": 0, "lapses": 0, "last_review": None}, srs.new_state())

    def test_new_card_answers(self):
        card = srs.new_state()
        again = srs.answer(card, "again", NOW, CFG)
        self.assertEqual({"state": "learning", "due": (NOW + timedelta(minutes=1)).isoformat(),
                          "step": 0, "interval": 0, "ease": None, "reps": 1, "lapses": 0,
                          "last_review": NOW.isoformat()}, again)
        hard = srs.answer(card, "hard", NOW, CFG)
        self.assertEqual(("learning", 0), (hard["state"], hard["step"]))
        self.assertEqual((NOW + timedelta(minutes=5.5)).isoformat(), hard["due"])
        good = srs.answer(card, "good", NOW, CFG)
        self.assertEqual(("learning", 1), (good["state"], good["step"]))
        self.assertEqual((NOW + timedelta(minutes=10)).isoformat(), good["due"])
        self.assertEqual(srs.new_state(), card)    # untouched

    def test_later_step(self):
        card = learning_card(step=1)
        hard = srs.answer(card, "hard", NOW, CFG)
        self.assertEqual(("learning", 1, (NOW + timedelta(minutes=10)).isoformat()),
                         (hard["state"], hard["step"], hard["due"]))
        again = srs.answer(card, "again", NOW, CFG)
        self.assertEqual((0, (NOW + timedelta(minutes=1)).isoformat()), (again["step"], again["due"]))
        good = srs.answer(card, "good", NOW, CFG)
        self.assertEqual({"state": "review", "due": "2026-09-15T04:00:00+03:30", "step": 0,
                          "interval": 1, "ease": 2.5, "reps": 2, "lapses": 0,
                          "last_review": NOW.isoformat()}, good)

    def test_hard_delay_single_step(self):
        card = srs.new_state()
        for steps, minutes in (([10], 15), ([2000], 3000), ([3000], 4440)):
            got = srs.answer(card, "hard", NOW, cfg(learning_steps=steps))
            self.assertEqual((NOW + timedelta(minutes=minutes)).isoformat(), got["due"], steps)

    def test_three_steps_hard_on_middle_step(self):
        three = cfg(learning_steps=[1, 5, 30])
        got = srs.answer(learning_card(step=1), "hard", NOW, three)
        self.assertEqual((NOW + timedelta(minutes=5)).isoformat(), got["due"])
        got = srs.answer(learning_card(step=1), "good", NOW, three)
        self.assertEqual((2, (NOW + timedelta(minutes=30)).isoformat()), (got["step"], got["due"]))

    def test_easy_graduates_with_easy_interval(self):
        seed = neutral_seed(0, ("easy",))
        got = srs.answer(srs.new_state(), "easy", NOW, CFG, seed=seed)
        self.assertEqual(("review", 4, 2.5), (got["state"], got["interval"], got["ease"]))
        self.assertEqual(srs.day_start(TODAY + 4, TEHRAN, CFG).isoformat(), got["due"])
        for n in range(50):
            got = srs.answer(srs.new_state(), "easy", NOW, CFG, seed=f"s{n}")
            self.assertIn(got["interval"], (3, 4, 5))
            self.assertEqual(srs.day_start(TODAY + got["interval"], TEHRAN, CFG).isoformat(),
                             got["due"])

    def test_empty_steps_graduate_at_once(self):
        none = cfg(learning_steps=[], graduating_interval=2, easy_interval=2)
        for rating in srs.RATINGS:
            got = srs.answer(srs.new_state(), rating, NOW, none)
            # Good graduates too, so Easy is at least a day longer than Good
            want = 3 if rating == "easy" else 2
            self.assertEqual(("review", want, 2.5), (got["state"], got["interval"], got["ease"]), rating)
        none = cfg(learning_steps=[], easy_interval=6)
        seed = neutral_seed(0, ("easy",))
        self.assertEqual(6, srs.answer(srs.new_state(), "easy", NOW, none, seed)["interval"])
        self.assertEqual(1, srs.answer(srs.new_state(), "again", NOW, none, seed)["interval"])

    def test_step_beyond_a_shortened_list(self):
        got = srs.answer(learning_card(step=5), "hard", NOW, CFG)
        self.assertEqual((1, (NOW + timedelta(minutes=10)).isoformat()), (got["step"], got["due"]))
        self.assertEqual("review", srs.answer(learning_card(step=5), "good", NOW, CFG)["state"])

    def test_graduation_before_rollover_is_due_the_same_morning(self):
        night = at(2026, 9, 15, 2, 0)          # still the 14th
        got = srs.answer(learning_card(step=1), "good", night, CFG)
        self.assertEqual("2026-09-15T04:00:00+03:30", got["due"])
        dawn = at(2026, 9, 15, 4, 0)           # the 15th
        got = srs.answer(learning_card(step=1), "good", dawn, CFG)
        self.assertEqual("2026-09-16T04:00:00+03:30", got["due"])

    def test_graduation_in_negative_offset(self):
        evening = at(2026, 9, 14, 23, 30, tz=NEW_YORK)
        got = srs.answer(learning_card(step=1), "good", evening, CFG)
        self.assertEqual("2026-09-15T04:00:00-05:00", got["due"])

    def test_graduating_interval_is_clamped_and_fuzzed(self):
        seed = neutral_seed(1, ("good",))
        got = srs.answer(learning_card(step=1), "good", NOW, cfg(graduating_interval=10), seed)
        self.assertEqual(10, got["interval"])
        seen = {srs.answer(learning_card(step=1), "good", NOW, cfg(graduating_interval=10),
                           f"s{n}")["interval"] for n in range(200)}
        self.assertEqual({9, 10, 11}, seen)
        capped = cfg(graduating_interval=10, maximum_interval=5)
        self.assertLessEqual(srs.answer(learning_card(step=1), "good", NOW, capped, "a")["interval"], 5)
        floor = cfg(minimum_interval=2)
        self.assertEqual(2, srs.answer(learning_card(step=1), "good", NOW, floor)["interval"])

    def test_easy_stays_after_good_when_both_graduate(self):
        # graduating 3 and easy 4 overlap once fuzzed (2..4 and 3..5)
        config = cfg(graduating_interval=3, easy_interval=4)
        corrected = 0
        for n in range(300):
            seed = f"s{n}"
            good = srs.answer(learning_card(step=1), "good", NOW, config, seed)["interval"]
            easy = srs.answer(learning_card(step=1), "easy", NOW, config, seed)["interval"]
            self.assertLess(good, easy, seed)
            if 4 - 1 + int(fuzz_frac(seed, "easy", 1) * 2 + 0.5) <= good:
                corrected += 1
        self.assertGreater(corrected, 0)
        # on a step Good does not finish, Easy is its own fuzzed interval
        for n in range(100):
            seed = f"s{n}"
            want = 4 - 1 + int(fuzz_frac(seed, "easy", 1) * 2 + 0.5)
            self.assertEqual(want, srs.answer(learning_card(step=0), "easy", NOW, config,
                                              seed)["interval"])

    def test_easy_stays_after_good_when_the_options_are_equal(self):
        # graduating 7 and easy 7 are both fuzzed over 6..8, independently
        config = cfg(graduating_interval=7, easy_interval=7)
        corrected = 0
        for n in range(300):
            seed = f"s{n}"
            card = learning_card(step=1)
            good = srs.answer(card, "good", NOW, config, seed)["interval"]
            easy = srs.answer(card, "easy", NOW, config, seed)["interval"]
            self.assertLess(good, easy, seed)
            shown = srs.preview(card, NOW, config, seed)
            self.assertLess(shown["good"]["seconds"], shown["easy"]["seconds"], seed)
            if 7 - 1 + int(fuzz_frac(seed, "easy", 1) * 2 + 0.5) <= good:
                corrected += 1
        self.assertGreater(corrected, 0)
        # at the maximum interval the two may meet, never cross
        capped = cfg(graduating_interval=7, easy_interval=7, maximum_interval=7)
        for n in range(50):
            got = srs.answer(learning_card(step=1), "easy", NOW, capped, f"s{n}")
            self.assertEqual(7, got["interval"])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            srs.answer(srs.new_state(), "okay", NOW, CFG)
        with self.assertRaises(ValueError):
            srs.answer(srs.new_state(), "good", datetime(2026, 9, 14, 15, 0), CFG)
        with self.assertRaises(ValueError):
            srs.preview(srs.new_state(), datetime(2026, 9, 14, 15, 0), CFG)

    def test_odd_state_reads_as_new(self):
        for state in (None, {}, {"state": "suspended", "reps": 3}):
            got = srs.answer(state, "again", NOW, CFG)
            self.assertEqual(("learning", 0), (got["state"], got["step"]))
        got = srs.answer({"state": "suspended", "reps": 3}, "again", NOW, CFG)
        self.assertEqual(4, got["reps"])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.seed = neutral_seed(5)

    def run_all(self, card, config=CFG, now=NOW, seed=None):
        seed = self.seed if seed is None else seed
        return {r: srs.answer(card, r, now, config, seed) for r in srs.RATINGS}

    def test_on_time(self):
        got = self.run_all(review_card())
        self.assertEqual((12, 2.35), (got["hard"]["interval"], got["hard"]["ease"]))
        self.assertEqual((25, 2.5), (got["good"]["interval"], got["good"]["ease"]))
        self.assertEqual((33, 2.65), (got["easy"]["interval"], got["easy"]["ease"]))  # 32.5 rounds up
        for rating in ("hard", "good", "easy"):
            r = got[rating]
            self.assertEqual(("review", 6, 0), (r["state"], r["reps"], r["lapses"]))
            self.assertEqual(srs.day_start(TODAY + r["interval"], TEHRAN, CFG).isoformat(), r["due"])

    def test_late_bonus(self):
        late = review_card(due=srs.day_start(TODAY - 4, TEHRAN, CFG))
        got = self.run_all(late)
        self.assertEqual(12, got["hard"]["interval"])       # hard ignores lateness
        self.assertEqual(30, got["good"]["interval"])       # (10 + 4/2) * 2.5
        self.assertEqual(46, got["easy"]["interval"])       # (10 + 4) * 2.5 * 1.3 = 45.5

    def test_late_is_counted_in_local_days(self):
        # Due 04:00 Tehran on the 13th, written in UTC: one day late on the 14th.
        due = srs.day_start(TODAY - 1, TEHRAN, CFG).astimezone(timezone.utc)
        got = self.run_all(review_card(due=due))
        self.assertEqual(round((10 + 0.5) * 2.5), got["good"]["interval"])  # 26.25 -> 26

    def test_early_review_has_no_negative_lateness(self):
        early = review_card(due=srs.day_start(TODAY + 3, TEHRAN, CFG))
        self.assertEqual(25, self.run_all(early)["good"]["interval"])

    def test_minimum_ordering(self):
        got = self.run_all(review_card(interval=1, ease=1.3))
        self.assertEqual([2, 3, 4], [got[r]["interval"] for r in ("hard", "good", "easy")])
        flat = cfg(hard_multiplier=1.0)
        got = self.run_all(review_card(interval=10), flat)
        self.assertEqual(10, got["hard"]["interval"])       # no I+1 floor at 1.0
        self.assertEqual(25, got["good"]["interval"])

    def test_interval_modifier(self):
        got = self.run_all(review_card(), cfg(interval_modifier=0.5))
        # hard: 10 * 1.2 * 0.5 = 6, but at least I + 1 since hard_multiplier > 1
        self.assertEqual([11, 13, 16], [got[r]["interval"] for r in ("hard", "good", "easy")])
        got = self.run_all(review_card(), cfg(interval_modifier=0.5, hard_multiplier=1.0))
        self.assertEqual([5, 13, 16], [got[r]["interval"] for r in ("hard", "good", "easy")])

    def test_ease_floor(self):
        got = self.run_all(review_card(ease=1.3), cfg(relearning_steps=[]))
        self.assertEqual(1.3, got["hard"]["ease"])
        self.assertEqual(1.3, got["again"]["ease"])
        got = self.run_all(review_card(ease=1.4))
        self.assertEqual(1.3, got["hard"]["ease"])
        self.assertEqual(1.3, got["again"]["ease"])

    def test_lapse_into_relearning(self):
        got = srs.answer(review_card(), "again", NOW, CFG, self.seed)
        self.assertEqual({"state": "relearning", "due": (NOW + timedelta(minutes=10)).isoformat(),
                          "step": 0, "interval": 1, "ease": 2.3, "reps": 6, "lapses": 1,
                          "last_review": NOW.isoformat()}, got)
        kept = srs.answer(review_card(), "again", NOW, cfg(new_interval=0.5), self.seed)
        self.assertEqual(5, kept["interval"])
        floor = srs.answer(review_card(), "again", NOW, cfg(minimum_interval=4), self.seed)
        self.assertEqual(4, floor["interval"])

    def test_lapse_without_relearning_steps(self):
        none = cfg(relearning_steps=[])
        got = srs.answer(review_card(lapses=2), "again", NOW, none, self.seed)
        self.assertEqual(("review", 1, 3, 2.3), (got["state"], got["interval"], got["lapses"], got["ease"]))
        self.assertEqual("2026-09-15T04:00:00+03:30", got["due"])
        seed = neutral_seed(5, ("again",))
        got = srs.answer(review_card(), "again", NOW, cfg(relearning_steps=[], new_interval=0.5), seed)
        self.assertEqual(5, got["interval"])
        self.assertEqual(srs.day_start(TODAY + 5, TEHRAN, CFG).isoformat(), got["due"])

    def test_maximum_interval(self):
        got = self.run_all(review_card(), cfg(maximum_interval=20))
        self.assertEqual([12, 20, 20], [got[r]["interval"] for r in ("hard", "good", "easy")])
        for n in range(100):
            got = self.run_all(review_card(interval=36000, ease=2.5), seed=f"s{n}")
            for rating in ("hard", "good", "easy"):
                self.assertLessEqual(got[rating]["interval"], 36500)

    def test_missing_ease_uses_starting_ease(self):
        card = review_card()
        card["ease"] = None
        self.assertEqual(25, self.run_all(card)["good"]["interval"])

    def test_unusable_ease_uses_starting_ease(self):
        # A hand-edited or imported ease so large that interval * ease is
        # infinite used to raise OverflowError from every answer and preview;
        # an integer too large for a float raised in math.isfinite.
        for ease in (1e6 + 1, 1e305, 1e308, 10 ** 400, float("inf"), float("nan"), 0, -2.5):
            with self.subTest(ease=ease):
                got = self.run_all(review_card(ease=ease))
                self.assertEqual((25, 2.5), (got["good"]["interval"], got["good"]["ease"]))
                for interval in (10, srs.MAX_DAYS):
                    card = review_card(interval=interval, ease=ease)
                    shown = srs.preview(card, NOW, CFG, self.seed)
                    self.assertEqual(list(srs.RATINGS), list(shown))

    def test_largest_kept_ease_stays_finite(self):
        # 1e6 is kept; with every multiplier at its highest, the longest
        # interval and a due in year 2 the arithmetic is still finite.
        worst = cfg(interval_modifier=10.0, easy_bonus=10.0, hard_multiplier=10.0)
        card = review_card(interval=srs.MAX_DAYS, ease=1e6, due=at(2, 1, 2, 4, tz=timezone.utc))
        shown = srs.preview(card, NOW, worst, self.seed)
        self.assertEqual(["100y", "100y", "100y"], [shown[r]["label"] for r in ("hard", "good", "easy")])
        self.assertEqual(1e6, srs.answer(card, "good", NOW, worst, self.seed)["ease"])

    def test_round_saturates(self):
        self.assertEqual(srs.MAX_DAYS, srs._round(float("inf")))
        self.assertEqual(0, srs._round(float("-inf")))
        self.assertEqual(0, srs._round(float("nan")))
        self.assertEqual((3, 2, 0), (srs._round(2.5), srs._round(2.4999), srs._round(-0.5)))

    def test_fuzz_is_deterministic_and_matches_the_formula(self):
        card = review_card(interval=40, ease=2.5, reps=7)
        for seed in ("abc123def456", "x", ""):
            got = srs.answer(card, "good", NOW, CFG, seed)
            self.assertEqual(got, srs.answer(card, "good", NOW, CFG, seed))
            ivl = 100
            delta = 5                                # 5 % of 100
            want = ivl - delta + int(fuzz_frac(seed, "good", 7) * 2 * delta + 0.5)
            self.assertEqual(want, got["interval"], seed)
        # The key uses the reps BEFORE the answer: another reps count, another spread.
        spread = {srs.answer(review_card(interval=40, reps=n), "good", NOW, CFG, "same")["interval"]
                  for n in range(60)}
        self.assertGreater(len(spread), 3)

    def test_fuzz_ranges(self):
        for interval, ease, low, high in ((10, 2.5, 24, 26), (40, 2.5, 95, 105)):
            seen = {srs.answer(review_card(interval=interval, ease=ease), "good", NOW, CFG,
                               f"s{n}")["interval"] for n in range(300)}
            self.assertEqual(set(range(low, high + 1)), seen, interval)

    def test_no_fuzz_below_three_days(self):
        config = cfg(graduating_interval=2)
        seen = {srs.answer(learning_card(step=1), "good", NOW, config, f"s{n}")["interval"]
                for n in range(100)}
        self.assertEqual({2}, seen)
        seen = {srs.answer(review_card(interval=1, ease=1.3), "hard", NOW, CFG, f"s{n}")["interval"]
                for n in range(100)}
        self.assertEqual({2}, seen)

    def test_order_survives_fuzz(self):
        # Pre-fuzz 2 < 3 < 4: raw fuzz would give good 2 or easy 3 for some seeds.
        card = review_card(interval=1, ease=1.3, reps=5)
        corrected = 0
        for n in range(300):
            seed = f"s{n}"
            got = self.run_all(card, seed=seed)
            hard, good, easy = (got[r]["interval"] for r in ("hard", "good", "easy"))
            self.assertLess(hard, good, seed)
            self.assertLess(good, easy, seed)
            raw_good = 3 - 1 + int(fuzz_frac(seed, "good", 5) * 2 + 0.5)
            raw_easy = 4 - 1 + int(fuzz_frac(seed, "easy", 5) * 2 + 0.5)
            if raw_good <= hard or raw_easy <= max(raw_good, hard + 1):
                corrected += 1
        self.assertGreater(corrected, 0)

    def test_hard_floor_survives_fuzz(self):
        # I = 3: hard is max(3.6, 4) = 4 before fuzz, which spreads it over
        # 3..5; the I + 1 floor keeps 3 out
        card = review_card(interval=3, ease=2.5, reps=5)
        seen, floored = set(), 0
        for n in range(300):
            seed = f"s{n}"
            seen.add(srs.answer(card, "hard", NOW, CFG, seed)["interval"])
            if 4 - 1 + int(fuzz_frac(seed, "hard", 5) * 2 + 0.5) < 4:
                floored += 1
        self.assertEqual({4, 5}, seen)
        self.assertGreater(floored, 0)
        # with hard_multiplier 1.0 there is no floor: fuzz may go below I
        flat = {srs.answer(review_card(interval=10), "hard", NOW, cfg(hard_multiplier=1.0),
                           f"s{n}")["interval"] for n in range(300)}
        self.assertEqual({9, 10, 11}, flat)


class RelearningTests(unittest.TestCase):
    def test_steps(self):
        card = relearning_card()
        again = srs.answer(card, "again", NOW, CFG)
        self.assertEqual(("relearning", 0, (NOW + timedelta(minutes=10)).isoformat(), 1, 2.3, 1),
                         (again["state"], again["step"], again["due"], again["interval"],
                          again["ease"], again["lapses"]))
        hard = srs.answer(card, "hard", NOW, CFG)
        self.assertEqual((NOW + timedelta(minutes=15)).isoformat(), hard["due"])
        good = srs.answer(card, "good", NOW, CFG)
        self.assertEqual(("review", 1, 2.3, "2026-09-15T04:00:00+03:30"),
                         (good["state"], good["interval"], good["ease"], good["due"]))
        easy = srs.answer(card, "easy", NOW, CFG)
        self.assertEqual(("review", 2, "2026-09-16T04:00:00+03:30"),
                         (easy["state"], easy["interval"], easy["due"]))

    def test_two_steps(self):
        two = cfg(relearning_steps=[10, 30])
        card = relearning_card()
        self.assertEqual((NOW + timedelta(minutes=20)).isoformat(),
                         srs.answer(card, "hard", NOW, two)["due"])
        good = srs.answer(card, "good", NOW, two)
        self.assertEqual(("relearning", 1, (NOW + timedelta(minutes=30)).isoformat()),
                         (good["state"], good["step"], good["due"]))
        hard = srs.answer(relearning_card(step=1), "hard", NOW, two)
        self.assertEqual((1, (NOW + timedelta(minutes=30)).isoformat()), (hard["step"], hard["due"]))
        self.assertEqual("review", srs.answer(relearning_card(step=1), "good", NOW, two)["state"])

    def test_graduates_to_stored_interval_fuzzed(self):
        seed = neutral_seed(6, ("good", "easy"))
        card = relearning_card(interval=10)
        self.assertEqual(10, srs.answer(card, "good", NOW, CFG, seed)["interval"])
        self.assertEqual(11, srs.answer(card, "easy", NOW, CFG, seed)["interval"])
        seen = {srs.answer(card, "good", NOW, CFG, f"s{n}")["interval"] for n in range(200)}
        self.assertEqual({9, 10, 11}, seen)

    def test_empty_steps(self):
        none = cfg(relearning_steps=[])
        card = relearning_card(interval=2)
        for rating, interval in (("again", 2), ("hard", 2), ("good", 2), ("easy", 3)):
            got = srs.answer(card, rating, NOW, none, neutral_seed(6, ("easy",)))
            self.assertEqual(("review", interval, 1), (got["state"], got["interval"], got["lapses"]),
                             rating)

    def test_easy_stays_after_good(self):
        # back to 20 days: Good is fuzzed over 18..22, Easy (21) over 20..22
        card = relearning_card(interval=20)
        corrected = 0
        for n in range(300):
            seed = f"s{n}"
            good = srs.answer(card, "good", NOW, CFG, seed)["interval"]
            easy = srs.answer(card, "easy", NOW, CFG, seed)["interval"]
            self.assertLess(good, easy, seed)
            if 21 - 1 + int(fuzz_frac(seed, "easy", 6) * 2 + 0.5) <= good:
                corrected += 1
        self.assertGreater(corrected, 0)
        # when Good only moves to the next step, Easy is its own fuzzed interval
        two = cfg(relearning_steps=[10, 30])
        for n in range(100):
            seed = f"s{n}"
            want = 21 - 1 + int(fuzz_frac(seed, "easy", 6) * 2 + 0.5)
            self.assertEqual(want, srs.answer(card, "easy", NOW, two, seed)["interval"])


class PreviewTests(unittest.TestCase):
    def states(self):
        return [
            srs.new_state(), learning_card(0), learning_card(1), review_card(),
            review_card(interval=1, ease=1.3),
            review_card(interval=200, due=srs.day_start(TODAY - 30, TEHRAN, CFG)),
            relearning_card(), relearning_card(interval=40),
        ]

    def test_preview_equals_answer(self):
        configs = [CFG, cfg(learning_steps=[], relearning_steps=[]),
                   cfg(learning_steps=[2, 20, 60], graduating_interval=5)]
        moments = [NOW, at(2026, 9, 15, 3, 59), at(2026, 9, 14, 23, 30, tz=NEW_YORK)]
        for config in configs:
            for now in moments:
                for state in self.states():
                    before = copy.deepcopy(state)
                    shown = srs.preview(state, now, config, seed="item1")
                    self.assertEqual(list(srs.RATINGS), list(shown))
                    self.assertEqual(before, state)
                    for rating in srs.RATINGS:
                        got = srs.answer(state, rating, now, config, seed="item1")
                        entry = shown[rating]
                        self.assertEqual(got["due"], entry["due"])
                        due = datetime.fromisoformat(got["due"])
                        seconds = int((due - now).total_seconds())
                        self.assertEqual(seconds, entry["seconds"])
                        self.assertGreaterEqual(entry["seconds"], 0)
                        if got["state"] == "review":
                            self.assertEqual(srs.label(got["interval"] * 86400), entry["label"])
                        else:
                            self.assertEqual(srs.label(seconds), entry["label"])

    def test_labels_like_anki(self):
        shown = srs.preview(srs.new_state(), NOW, CFG, seed=neutral_seed(0, ("easy",)))
        self.assertEqual(["1m", "6m", "10m", "4d"], [shown[r]["label"] for r in srs.RATINGS])
        shown = srs.preview(learning_card(1), NOW, CFG)
        self.assertEqual("1d", shown["good"]["label"])
        self.assertEqual(13 * 3600, shown["good"]["seconds"])   # until 04:00 tomorrow


def entry(item_id, created, state):
    return (item_id, created.isoformat() if isinstance(created, datetime) else created, state)


def learning_due(due):
    card = learning_card()
    card["due"] = due.isoformat()
    return card


class QueueTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual({"next": None, "counts": {"new": 0, "learning": 0, "review": 0},
                          "next_due": None}, srs.queue([], NOW, CFG, {"new": 0, "review": 0}))

    def test_priority_learning_then_review_then_new(self):
        old = at(2026, 1, 1)
        entries = [
            entry("n1", old, srs.new_state()),
            entry("r1", old, review_card()),
            entry("l1", old, learning_due(NOW - timedelta(minutes=1))),
        ]
        got = srs.queue(entries, NOW, CFG, {"new": 0, "review": 0})
        self.assertEqual("l1", got["next"])
        self.assertEqual({"new": 1, "learning": 1, "review": 1}, got["counts"])
        self.assertEqual("r1", srs.queue(entries[:2], NOW, CFG, {"new": 0, "review": 0})["next"])
        self.assertEqual("n1", srs.queue(entries[:1], NOW, CFG, {"new": 0, "review": 0})["next"])

    def test_orderings(self):
        t0 = at(2026, 1, 1, 12, 0)
        learning = [entry("lb", t0, learning_due(NOW - timedelta(minutes=2))),
                    entry("la", t0, learning_due(NOW - timedelta(minutes=5)))]
        self.assertEqual("la", srs.queue(learning, NOW, CFG)["next"])
        same_due = review_card()
        reviews = [entry("rb", t0 + timedelta(seconds=1), same_due),
                   entry("ra", t0 + timedelta(seconds=2), same_due),
                   entry("rc", t0, review_card(due=srs.day_start(TODAY - 1, TEHRAN, CFG)))]
        self.assertEqual("rc", srs.queue(reviews, NOW, CFG)["next"])
        self.assertEqual("rb", srs.queue(reviews[:2], NOW, CFG)["next"])
        news = [entry("nb", t0, srs.new_state()), entry("na", t0, srs.new_state()),
                entry("nz", t0 - timedelta(microseconds=1), srs.new_state())]
        self.assertEqual("nz", srs.queue(news, NOW, CFG)["next"])
        self.assertEqual("na", srs.queue(news[:2], NOW, CFG)["next"])
        # created compared as moments, not strings: 12:00+03:30 is before 09:00Z
        mixed = [entry("late", at(2026, 1, 1, 9, 0, tz=timezone.utc), srs.new_state()),
                 entry("early", at(2026, 1, 1, 12, 0), srs.new_state())]
        self.assertEqual("early", srs.queue(mixed, NOW, CFG)["next"])

    def test_limits(self):
        t0 = at(2026, 1, 1)
        news = [entry(f"n{i}", t0 + timedelta(seconds=i), srs.new_state()) for i in range(5)]
        reviews = [entry(f"r{i}", t0 + timedelta(seconds=i), review_card()) for i in range(5)]
        config = cfg(new_per_day=3, reviews_per_day=4)
        got = srs.queue(news + reviews, NOW, config, {"new": 1, "review": 1})
        self.assertEqual({"new": 2, "learning": 0, "review": 3}, got["counts"])
        got = srs.queue(news + reviews, NOW, config, {"new": 7, "review": 9})
        self.assertEqual({"new": 0, "learning": 0, "review": 0}, got["counts"])
        self.assertIsNone(got["next"])
        # held back by today's limit: they come back when the next day starts
        self.assertEqual("2026-09-15T04:00:00+03:30", got["next_due"])
        closed = cfg(new_per_day=0)
        got = srs.queue(news, NOW, closed, {"new": 0, "review": 0})
        self.assertEqual((None, None), (got["next"], got["next_due"]))
        self.assertEqual({"new": 3, "learning": 0, "review": 0},
                         srs.queue(news, NOW, config, None)["counts"])

    def test_learn_ahead(self):
        t0 = at(2026, 1, 1)
        soon = entry("soon", t0, learning_due(NOW + timedelta(minutes=15)))
        got = srs.queue([soon], NOW, CFG, {"new": 0, "review": 0})
        self.assertEqual(("soon", 1, None), (got["next"], got["counts"]["learning"], got["next_due"]))
        # something else to do comes first
        got = srs.queue([soon, entry("n", t0, srs.new_state())], NOW, CFG)
        self.assertEqual("n", got["next"])
        far = entry("far", t0, learning_due(NOW + timedelta(minutes=25)))
        got = srs.queue([far], NOW, CFG)
        self.assertEqual((None, 0), (got["next"], got["counts"]["learning"]))
        self.assertEqual((NOW + timedelta(minutes=25)).isoformat(), got["next_due"])
        got = srs.queue([soon, far], NOW, cfg(learn_ahead_minutes=0))
        self.assertEqual((None, 0), (got["next"], got["counts"]["learning"]))
        self.assertEqual((NOW + timedelta(minutes=15)).isoformat(), got["next_due"])

    def test_next_due_is_the_earliest_uncounted(self):
        t0 = at(2026, 1, 1)
        entries = [
            entry("tomorrow", t0, review_card(due=srs.day_start(TODAY + 1, TEHRAN, CFG))),
            entry("week", t0, review_card(due=srs.day_start(TODAY + 7, TEHRAN, CFG))),
            entry("hour", t0, learning_due(NOW + timedelta(hours=1))),
            entry("counted", t0, learning_due(NOW + timedelta(minutes=5))),
        ]
        got = srs.queue(entries, NOW, CFG)
        self.assertEqual("counted", got["next"])
        self.assertEqual((NOW + timedelta(hours=1)).isoformat(), got["next_due"])
        got = srs.queue(entries[:2], NOW, CFG)
        self.assertEqual((None, "2026-09-15T04:00:00+03:30"), (got["next"], got["next_due"]))
        # a due written in another offset is reported in now's
        utc = review_card(due=srs.day_start(TODAY + 2, TEHRAN, CFG).astimezone(timezone.utc))
        got = srs.queue([entry("u", t0, utc)], NOW, CFG)
        self.assertEqual("2026-09-16T04:00:00+03:30", got["next_due"])

    def test_review_becomes_due_at_the_local_rollover(self):
        t0 = at(2026, 1, 1)
        card = review_card(due=srs.day_start(TODAY + 1, TEHRAN, CFG))
        just_before = srs.queue([entry("r", t0, card)], at(2026, 9, 15, 3, 59, 59), CFG)
        self.assertEqual((None, 0), (just_before["next"], just_before["counts"]["review"]))
        self.assertEqual("2026-09-15T04:00:00+03:30", just_before["next_due"])
        on_time = srs.queue([entry("r", t0, card)], at(2026, 9, 15, 4, 0), CFG)
        self.assertEqual(("r", 1, None), (on_time["next"], on_time["counts"]["review"],
                                          on_time["next_due"]))

    def test_due_day_taken_in_nows_timezone(self):
        # 01:00Z on the 15th is 04:30 on the 15th in Tehran: tomorrow there,
        # though its own (UTC) date minus the rollover hours is still the 14th.
        t0 = at(2026, 1, 1)
        card = review_card()
        card["due"] = "2026-09-15T01:00:00+00:00"
        night = at(2026, 9, 15, 2, 0)          # the 14th, locally
        got = srs.queue([entry("r", t0, card)], night, CFG)
        self.assertEqual((None, 0), (got["next"], got["counts"]["review"]))
        # it comes due when the 15th starts (see the test below)
        self.assertEqual("2026-09-15T04:00:00+03:30", got["next_due"])

    def test_next_due_of_a_review_is_the_start_of_its_day(self):
        # a due that is not at the rollover hour is counted from the start of
        # its day, so that is when the next exercise really comes
        t0 = at(2026, 1, 1)
        card = review_card()
        card["due"] = "2026-09-15T01:00:00+00:00"          # 04:30 on the 15th in Tehran
        got = srs.queue([entry("r", t0, card)], at(2026, 9, 15, 2, 0), CFG)
        self.assertEqual("2026-09-15T04:00:00+03:30", got["next_due"])
        at_that_moment = srs.queue([entry("r", t0, card)], datetime.fromisoformat(got["next_due"]), CFG)
        self.assertEqual(("r", 1), (at_that_moment["next"], at_that_moment["counts"]["review"]))

    def test_unreadable_due_and_odd_rows(self):
        t0 = at(2026, 1, 1)
        broken = learning_card()
        broken["due"] = "garbage"
        got = srs.queue([entry("b", "not a date", broken), entry("n", None, None)], NOW, CFG)
        self.assertEqual("b", got["next"])
        self.assertEqual({"new": 1, "learning": 1, "review": 0}, got["counts"])
        with self.assertRaises(ValueError):
            srs.queue([], datetime(2026, 9, 14), CFG)


class RolloverDueTests(unittest.TestCase):
    """A review due written by day_start keeps its date when the offset changes.

    A card answered in summer time gets day_start's 04:00 with +02:00; read
    after the clocks went back, converting it to +01:00 gives 03:00, before
    the rollover, which is the day before."""

    SUMMER = "2026-11-02T04:00:00+02:00"
    WINTER = "2026-11-02T04:00:00+01:00"
    NOV2 = datetime(2026, 11, 2).toordinal()

    def card(self, due, interval=13):
        return {"state": "review", "due": due, "step": 0, "interval": interval, "ease": 2.5,
                "reps": 3, "lapses": 0, "last_review": None}

    def test_the_server_writes_the_summer_offset(self):
        # the premise, through answer(): what really lands on disk in October
        card = self.card(at(2026, 10, 20, 4, tz=CEST).isoformat(), interval=5)
        got = srs.answer(card, "good", at(2026, 10, 20, 15, tz=CEST), CFG, neutral_seed(3, ("good",)))
        self.assertEqual((13, self.SUMMER), (got["interval"], got["due"]))

    def test_due_day(self):
        for now in (at(2026, 11, 1, 15, tz=CET), at(2026, 11, 2, 15, tz=CET), at(2026, 10, 20, tz=CEST)):
            for due in (self.SUMMER, datetime.fromisoformat(self.SUMMER), self.WINTER):
                self.assertEqual(self.NOV2, srs.due_day(due, now, CFG), (now, due))
        midnight = cfg(rollover_hour=0)
        self.assertEqual(self.NOV2, srs.due_day("2026-11-02T00:00:00+02:00", at(2026, 11, 1, 12, tz=CET),
                                                midnight))
        # read in New York, 04:00+02:00 is 21:00 on the 1st: kept on the 2nd
        # while 04:00 is the rollover hour, converted like any instant when not
        in_new_york = at(2026, 11, 1, 12, tz=NEW_YORK)
        self.assertEqual(self.NOV2, srs.due_day(self.SUMMER, in_new_york, CFG))
        self.assertEqual(self.NOV2 - 1, srs.due_day(self.SUMMER, in_new_york, cfg(rollover_hour=3)))
        # a day_start written at +14:00 keeps its date, though in Tehran that
        # moment is still the 14th
        self.assertEqual(TODAY + 1, srs.due_day("2026-09-15T04:00:00+14:00", NOW, CFG))
        # not exactly the rollover hour: converted to now's timezone first
        for due in ("2026-09-15T04:00:01+14:00", "2026-09-15T04:00:00.5+14:00", "2026-09-15T05:00:00+14:00"):
            self.assertEqual(TODAY, srs.due_day(due, NOW, CFG), due)
        self.assertEqual(TODAY + 1, srs.due_day("2026-09-15T01:00:00+00:00", at(2026, 9, 15, 2), CFG))
        # a due that cannot be read is due today
        for due in (None, "", "garbage", 5, "9999-12-31T23:00:00-05:00"):
            self.assertEqual(TODAY, srs.due_day(due, NOW, CFG), due)
        with self.assertRaises(ValueError):
            srs.due_day(self.SUMMER, datetime(2026, 11, 1, 15), CFG)

    def test_queue_after_the_clocks_went_back(self):
        t0 = at(2026, 1, 1)
        rows = [entry("x", t0, self.card(self.SUMMER))]
        eve = srs.queue(rows, at(2026, 11, 1, 15, tz=CET), CFG)
        self.assertEqual((None, 0), (eve["next"], eve["counts"]["review"]))
        self.assertEqual(self.WINTER, eve["next_due"])
        early = srs.queue(rows, at(2026, 11, 2, 3, 59, tz=CET), CFG)
        self.assertEqual((None, 0, self.WINTER), (early["next"], early["counts"]["review"], early["next_due"]))
        day = srs.queue(rows, at(2026, 11, 2, 4, tz=CET), CFG)
        self.assertEqual(("x", 1, None), (day["next"], day["counts"]["review"], day["next_due"]))

    def test_rollover_at_midnight(self):
        midnight = cfg(rollover_hour=0)
        rows = [entry("x", at(2026, 1, 1), self.card("2026-11-02T00:00:00+02:00"))]
        eve = srs.queue(rows, at(2026, 11, 1, 23, 30, tz=CET), midnight)
        self.assertEqual((None, "2026-11-02T00:00:00+01:00"), (eve["next"], eve["next_due"]))
        self.assertEqual("x", srs.queue(rows, at(2026, 11, 2, 0, tz=CET), midnight)["next"])

    def test_not_late_on_its_own_day(self):
        now = at(2026, 11, 2, 15, tz=CET)
        seed = neutral_seed(3)
        summer = srs.preview(self.card(self.SUMMER), now, CFG, seed)
        winter = srs.preview(self.card(self.WINTER), now, CFG, seed)
        self.assertEqual(winter, summer)
        self.assertEqual(33, srs.answer(self.card(self.SUMMER), "good", now, CFG, seed)["interval"])  # 13 * 2.5
        # a card really a day late still gets the bonus
        late = srs.answer(self.card("2026-11-01T04:00:00+02:00"), "good", now, CFG, seed)
        self.assertEqual(34, late["interval"])                                    # 13.5 * 2.5


class DateRangeTests(unittest.TestCase):
    """Imported or hand-edited dates at the edge of datetime's range.

    Converting them to UTC or to now's offset overflowed, which took down
    every queue over the deck; they now read as unreadable."""

    EDGES = ("9999-12-31T23:00:00-05:00", "0001-01-01T00:30:00+05:00", "0001-06-01T00:00:00+00:00",
             "9999-01-01T00:00:00+00:00", "0001-01-01T00:00:00", "9999-12-31T23:59:59",
             "0002-01-01T00:00:00+00:01")

    def test_out_of_range_reads_as_unreadable(self):
        for text in self.EDGES:
            self.assertIsNone(srs.due_at({"due": text}), text)
        for text in ("0002-01-01T00:00:00+00:00", "9998-12-31T23:59:59+00:00",
                     "9999-01-01T04:00:00+23:59", "0001-12-31T23:00:00-23:59"):
            self.assertIsNotNone(srs.due_at({"due": text}), text)

    def test_scheduler_survives_edge_dates(self):
        t0 = at(2026, 1, 1)
        for text in self.EDGES:
            with self.subTest(text=text):
                review = review_card()
                review["due"] = text
                learning = learning_card()
                learning["due"] = text
                rows = [entry("r", t0, review), entry("l", t0, learning), entry("n", text, srs.new_state()),
                        entry("m", t0, srs.new_state())]
                got = srs.queue(rows, NOW, CFG)
                # read as due now; an unreadable created sorts after readable ones
                self.assertEqual(("l", {"new": 2, "learning": 1, "review": 1}), (got["next"], got["counts"]))
                self.assertEqual("m", srs.queue(rows[2:], NOW, CFG)["next"])
                seed = neutral_seed(5)
                self.assertEqual(25, srs.answer(review, "good", NOW, CFG, seed)["interval"])
                srs.preview(review, NOW, CFG, seed)
                history = [{"at": text, "before": "review"}]
                self.assertEqual({"new": 0, "review": 0}, srs.today_counts([history], NOW, CFG))
        # just inside the range, in the most distant offsets: still no overflow
        for text in ("9999-01-01T04:00:00+23:59", "0001-12-31T04:00:00-23:59", "0002-01-01T00:00:00+00:00"):
            with self.subTest(text=text):
                for now in (NOW, at(2026, 9, 14, tz=timezone(timedelta(hours=23, minutes=59))),
                            at(2026, 9, 14, tz=timezone(-timedelta(hours=23, minutes=59)))):
                    review = review_card()
                    review["due"] = text
                    srs.queue([entry("r", text, review)], now, CFG)
                    srs.preview(review, now, CFG, "x")
                    srs.today_counts([[{"at": text, "before": "new"}]], now, CFG)


class TodayCountsTests(unittest.TestCase):
    def test_counts_by_local_day(self):
        histories = [
            [{"at": at(2026, 9, 14, 9, 0).isoformat(), "before": "new"},
             {"at": at(2026, 9, 14, 9, 1).isoformat(), "before": "learning"},
             {"at": at(2026, 9, 14, 9, 11).isoformat(), "before": "learning"}],
            [{"at": at(2026, 9, 13, 10, 0).isoformat(), "before": "new"},       # yesterday
             {"at": at(2026, 9, 14, 3, 59).isoformat(), "before": "review"},    # before rollover
             {"at": at(2026, 9, 14, 4, 0).isoformat(), "before": "review"},
             {"at": "2026-09-14T11:00:00Z", "before": "review"},               # 14:30 local
             {"at": at(2026, 9, 14, 12, 0).isoformat(), "before": "relearning"}],
            [],
            [{"at": "garbage", "before": "new"}, {"before": "new"}, "oops", {"at": None}],
        ]
        self.assertEqual({"new": 1, "review": 2}, srs.today_counts(histories, NOW, CFG))
        self.assertEqual({"new": 0, "review": 0}, srs.today_counts([], NOW, CFG))
        # just before the next rollover it is still the 14th
        self.assertEqual({"new": 1, "review": 2},
                         srs.today_counts(histories, at(2026, 9, 15, 3, 59), CFG))
        self.assertEqual({"new": 0, "review": 0},
                         srs.today_counts(histories, at(2026, 9, 15, 4, 0), CFG))

    def test_negative_offset(self):
        # 03:00Z on the 15th is 22:00 on the 14th in New York.
        histories = [[{"at": "2026-09-15T03:00:00+00:00", "before": "new"}]]
        evening = at(2026, 9, 14, 23, 0, tz=NEW_YORK)
        self.assertEqual({"new": 1, "review": 0}, srs.today_counts(histories, evening, CFG))


class FlowTests(unittest.TestCase):
    def test_a_card_through_its_life(self):
        now, state, seed = NOW, srs.new_state(), "0123456789ab"
        for rating in ("good", "good"):
            state = srs.answer(state, rating, now, CFG, seed)
            now = datetime.fromisoformat(state["due"])
        self.assertEqual(("review", 1), (state["state"], state["interval"]))
        intervals = []
        for _ in range(5):
            now = datetime.fromisoformat(state["due"]) + timedelta(hours=6)
            q = srs.queue([("c", NOW.isoformat(), state)], now, CFG)
            self.assertEqual("c", q["next"])
            state = srs.answer(state, "good", now, CFG, seed)
            intervals.append(state["interval"])
            self.assertTrue(state["due"].endswith("T04:00:00+03:30"), state["due"])
        self.assertEqual(sorted(intervals), intervals)
        self.assertGreater(intervals[-1], 30)
        self.assertEqual(7, state["reps"])
        state = srs.answer(state, "again", now, CFG, seed)
        self.assertEqual(("relearning", 1, 1, 2.3), (state["state"], state["interval"],
                                                    state["lapses"], state["ease"]))
        now = datetime.fromisoformat(state["due"])
        self.assertEqual("c", srs.queue([("c", NOW.isoformat(), state)], now, CFG)["next"])
        state = srs.answer(state, "good", now, CFG, seed)
        self.assertEqual(("review", 1), (state["state"], state["interval"]))


if __name__ == "__main__":
    unittest.main()
