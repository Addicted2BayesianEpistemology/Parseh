Parseh transcript-review skills

The suspect-word package is parseh-asr-correction; the whole-text package is
parseh-asr-audit. Extract the chosen skill folder under the endpoint user's
.agents/skills/ directory, or create an Agent Skill in Unsloth Studio using
its name, description and instructions from SKILL.md. Enable it. In a Studio
chat select @parseh-asr-correction or @parseh-asr-audit.

Parseh can install a new skill through Unsloth's authenticated Skills API.
Select the skill to check/install in the review page, then use Install in
saved endpoint. Existing skills are never overwritten: inspect or update
them in Studio yourself. Configure the Unsloth Agent Skills adapter first,
then choose Use installed skill for the chosen review. Only read_skill is
enabled for these requests, with MCP disabled.

Other software: use its own Agent Skills import mechanism. A skill available
in a chat UI may not be available through that software's API. Generic
OpenAI-compatible endpoints use Parseh's short prompt.

Skills provide instructions. They do not train weights, improve the model's
base language competence, or guarantee that a correction is right.

The additional parseh-asr-workspace skill describes a two-pass file-and-code
review. Parseh loads it automatically for workspace review and provides isolated
Python tools. Download it from Correction skill for other software; that software
must provide its own file/code environment. The installed-skill checkbox applies
to the two sentence-review methods above.

The workspace package includes scripts/review.py, supplied as review.py in each
downloaded text/CSV workspace. It needs only Python's standard library. Use
review.check() while editing and review.check(require_complete=True), or
python review.py --check --complete, before returning the result CSV. These
checks preserve source spans and required coverage, not linguistic accuracy.
