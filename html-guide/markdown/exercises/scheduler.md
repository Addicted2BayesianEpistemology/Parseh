---
title: The scheduler
weight: 8
description: How a deck decides when an exercise comes back — Anki's SM-2, step by step, with a worked example.
---

The decks use **Anki's own scheduler**, SM-2 as Anki's v2 and v3 schedulers
run it, so a habit formed in Anki carries over, and a number you know from
Anki means the same here. This page gives the rules with the deck's default
[options](options.md); every number in *italics* below is one of those
options.

## Four states

| State | What it means |
|---|---|
| **new** | never answered |
| **learning** | answered, and coming back within minutes, through the learning steps |
| **review** | known: coming back after days, then weeks and months |
| **relearning** | a review you forgot, going through a short step before it is a review again |

A deck's counts join *learning* and *relearning*: both come back within
minutes, and both are red on the study page.

## Learning: the first minutes

A new exercise goes through the **learning steps** — by default *1 minute,
then 10 minutes*:

- **Again** sends it back to the first step: it returns in a minute.
- **Hard** repeats the step it is on. On the first step it waits halfway
  between the first two steps — 5½ minutes, shown as `6m`. (With a single
  step, Hard waits half as long again as that step.)
- **Good** moves it to the next step; **Good on the last step graduates it**
  to review, due in *1 day* (the **graduating interval**).
- **Easy** graduates it at once, due in *4 days* (the **easy interval**) —
  and always at least a day later than Good would have.

With no learning steps at all, an exercise graduates the first time you
press Good.

## Review: the waits grow

A review waits whole days, and each exercise carries its own **ease**, a
multiplier that starts at *2.5* when it graduates:

- **Good** multiplies the interval by the ease: 4 days become 10.
- **Hard** multiplies it by *1.2* only, and lowers the ease by 0.15.
- **Easy** multiplies it by the ease **and** by *1.3* (the **easy bonus**),
  and raises the ease by 0.15.
- The three are kept apart: Hard always gives at least one day more than
  the interval had, Good at least one day more than Hard, Easy at least one
  day more than Good.
- **Answered late**, an exercise gets credit for the days it waited beyond
  its due date: half of them on Good, all of them on Easy. Knowing a thing
  after a longer wait than planned says it is better known than planned.
- No interval is longer than *36,500 days* (the **maximum interval**) or
  shorter than *1 day*.

An exercise you keep knowing thus comes back after 1 day, 3 or 4, about 10,
about 25, two months, five… — and one you find hard sees its ease fall, and
its waits grow more slowly.

## Lapses: when you forget

**Again** on a review is a **lapse**. The ease drops by 0.20 — never below
*1.3*, the **minimum ease** — and the exercise **relearns**: it comes back
after the *10-minute* relearning step. Good on that step puts it back into
review, due in a day; Easy, a day later than that; Again, Hard and Good on
the step work as in learning.

The deck counts the lapses: the list on the deck's page shows them beside
the reviews, `4 reviews · 1 lapse`.

## The spread

Intervals of three days and more are moved by a few percent — up to 15%
for a week or less, 10% up to twenty days, 5% beyond, and always at least a
day — so that forty exercises added on the same evening do not all fall due
on the same morning.

Unlike Anki, the spread is not drawn by lot. It is worked out from the
exercise itself, the button and how many times it has been answered, so the
label on each rating button is **exactly** the interval the answer will get.

## The day starts at four

A deck's day begins at *04:00*, local time, as Anki's does. An answer given
at one in the morning counts for the evening before, and an exercise due
"tomorrow" is due from four o'clock tomorrow morning — for the whole of that
day. The change to and from summer time moves nothing: a review due on a
day stays due on that day.

## Daily limits

At most *20* new exercises and *200* reviews a day, counted from the answers
already given that day. What a limit holds back waits for the next day —
the decks page then says *next exercise tomorrow* — and learning steps are
never limited, since holding back an exercise you are in the middle of
learning would undo the learning. A limit set to 0 holds its exercises back
every day: a deck with 0 new exercises a day studies only what it already
knows.

## What comes next {#what-comes-next}

Of everything due, the study page shows first a learning step that is due,
then a review that is due — the one that has waited longest first — then a
new exercise, in the order they were added. When none of those is left
today, a learning step due within the next *20 minutes* is shown at once
rather than making you wait: Anki calls that **learning ahead**.

## A worked example

One exercise, answered each time on the day it fell due, with the deck's
default options. The last four columns are what the four buttons offered
for the *next* answer — what you would have seen on the study page.

| You press | It is now | Again | Hard | Good | Easy |
|---|---|---|---|---|---|
| — | new | 1m | 6m | 10m | 4d |
| Good | learning, step 2 | 1m | 10m | 1d | 3d |
| Good | review, 1 day, ease 2.5 | 10m | 2d | 4d | 5d |
| Good | review, 4 days, ease 2.5 | 10m | 6d | 10d | 13d |
| Good | review, 10 days, ease 2.5 | 10m | 13d | 24d | 1.1mo |
| Good | review, 24 days, ease 2.5 | 10m | 29d | 1.9mo | 2.7mo |
| Again | relearning, ease 2.3 | 10m | 15m | 1d | 2d |
| Good | review, 1 day, ease 2.3 | 10m | 2d | 3d | 5d |
| Good | review, 3 days, ease 2.3 | 10m | 4d | 7d | 9d |
| Hard | review, 4 days, ease 2.15 | 10m | 5d | 9d | 11d |
| Easy | review, 11 days, ease 2.3 | 10m | 12d | 26d | 1.1mo |

The spread makes another exercise's numbers differ by a day here and
there; the shape is the same. Note the lapse: after 24 days the exercise
starts again from a day — the *new interval* option decides how much of the
old interval a lapse keeps, and by default it keeps none — but with an ease
a little lower, so it climbs more carefully the second time.

## For those who know Anki

The deck keeps Anki's defaults and its rules, with four small differences:

- the spread is computed, not random, so the labels are exact;
- halves round up (Anki rounds its own way);
- the minimum interval holds for every interval, not only after a lapse;
- a button's label for a day interval reads the interval (`1d`), not the
  hours left until the next four o'clock.

The scheduler is `markdown/app/srs.py`, and it keeps every answer: each
exercise's `schedule/<id>.json` holds its state and the whole list of your
answers, with the rating, whether the check found you right, and the
interval and ease that followed.
