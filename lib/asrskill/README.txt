Parseh ASR correction skill

Unsloth Studio: extract parseh-asr-correction/SKILL.md under your user
.agents/skills/ directory, or create an Agent Skill named
parseh-asr-correction in Studio with the description and instructions from
SKILL.md. Enable it. In a Studio chat select @parseh-asr-correction.

Parseh can install this exact skill through Unsloth's authenticated Skills
API with the Install in saved endpoint button. It never overwrites an existing
skill. Configure the Unsloth Agent Skills adapter in LLM Integration first,
then choose Use installed correction skill on the correction review page.
Only the read_skill tool is enabled for these requests, with MCP disabled.

Other software: use its own Agent Skills import mechanism. Installing a skill
in a chat UI does not necessarily make it available to that software's API.
Generic OpenAI-compatible endpoints continue to use Parseh's short prompt.

Skills provide reusable instructions. They do not train or upgrade the model.
