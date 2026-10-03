# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved Studio links at one configured endpoint; explicit installed-model loads."""
import threading

import llmadapter
import llmconfig
from llmconfig import LLMError

SWITCH = threading.Lock()


def _configured(root):
    c = llmconfig.load(root)
    if c is None:
        raise LLMError("unconfigured", "Configure the endpoint on the Parseh host first.")
    return c


def save(body, root=None):
    if not isinstance(body, dict) or set(body) != {"name", "link"}:
        raise LLMError("bad-profile", "Save a profile name and Studio link only.")
    with llmconfig.LOCK:
        c = _configured(root)
        imported = llmconfig.share_link(body["link"])
        name = body["name"] or (imported["model_hint"].split("/")[-1] + " " + imported["gguf_variant"])[:100]
        p = llmconfig.model_profile(body["link"], name, c["base_url"])
        rows = [r for r in c.get("model_profiles", []) if r["id"] != p["id"]]
        c["model_profiles"] = rows + [p]
        llmconfig._write(llmconfig.validate(c), root)
        return dict(llmconfig.view(root), saved_profile=p["id"])


def _ident(body):
    if not isinstance(body, dict) or set(body) != {"profile_id"} or not isinstance(body["profile_id"], str):
        raise LLMError("bad-profile", "Select a saved profile ID only.")
    return body["profile_id"]


def remove(body, root=None):
    ident = _ident(body)
    with llmconfig.LOCK:
        c = _configured(root)
        if c.get("pending_profile") == ident:
            raise LLMError("profile-pending", "Apply this pending profile or select a loaded model before removing it.")
        c["model_profiles"] = [r for r in c.get("model_profiles", []) if r["id"] != ident]
        if c.get("selected_profile") == ident:
            c.pop("selected_profile", None)
        c["review_models"] = {t: s for t, s in c.get("review_models", {}).items() if s["profile_id"] != ident}
        llmconfig._write(llmconfig.validate(c), root)
        return llmconfig.view(root)


def apply(body, root=None, expected=None):
    ident = _ident(body)
    if not SWITCH.acquire(blocking=False):
        raise LLMError("model-switch-busy", "Another model profile is loading. Wait for it to finish.")
    try:
        with llmconfig.LOCK:
            old = _configured(root)
            if expected is not None and old != expected:
                raise LLMError("settings-changed", "The LLM settings changed. Inspect the destination and choose review again.")
            p = next((r for r in old.get("model_profiles", []) if r["id"] == ident), None)
        if p is None:
            raise LLMError("bad-profile", "This saved model profile no longer exists.")
        client = llmadapter.adapter(old)
        if not isinstance(client, llmadapter.UnslothStudio):
            raise LLMError("studio-unavailable", "Choose an Unsloth Studio API adapter on the host to load saved model profiles.")
        info, local = client.resolve_profile(p)
        with llmconfig.LOCK:
            if llmconfig.load(root) != old:
                raise LLMError("settings-changed", "The connection changed before loading this profile. Select it again.")
            pending = dict(old, selected_model=info["model_hint"], pending_profile=ident)
            pending.pop("selected_profile", None)
            # Invalidate earlier correction requests BEFORE the endpoint changes.
            # A failed/unfinished load remains pending, including after restart.
            llmconfig._write(llmconfig.validate(pending), root)
        applied = client.load_profile(info, local)
        with llmconfig.LOCK:
            if llmconfig.load(root) != pending:
                raise LLMError("settings-changed", "The connection changed during loading. Inspect the endpoint's active model before reviewing text.")
            ready = dict(pending, selected_profile=ident, studio_link=p["link"],
                         context_tokens=applied["context_tokens"])
            ready.pop("pending_profile", None)
            llmconfig._write(llmconfig.validate(ready), root)
            return dict(llmconfig.view(root), applied_profile=applied,
                        say="The installed model profile is loaded." +
                            (" Unsloth adjusted the context length; Parseh uses the reported length." if applied["context_adjusted"] else ""))
    finally:
        SWITCH.release()


def prepare(body, root=None):
    """Explicit review action: load only its saved installed-model profile."""
    if not isinstance(body, dict) or set(body) != {"task", "connection_id"} or body.get("task") not in ("suspect", "full"):
        raise LLMError("bad-review", "Choose a saved review task only.")
    with llmconfig.LOCK:
        c = _configured(root)
        if body["connection_id"] != llmconfig.revision(c):
            raise LLMError("settings-changed", "The LLM settings changed. Inspect the current destination and choose review again.")
        setting = c.get("review_models", {}).get(body["task"])
        needs_load = setting and setting["profile_id"] and (c.get("selected_profile") != setting["profile_id"] or c.get("pending_profile"))
        if not needs_load:
            llmconfig.for_review(c, body["task"])
            return llmconfig.view(root)
    return apply({"profile_id": setting["profile_id"]}, root, expected=c)
