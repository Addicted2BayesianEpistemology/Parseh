# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-local, optional LLM connection. Never put credentials in prefs or views."""
import hashlib
import json
import os
import secrets
import threading
import urllib.parse

STORE_FORMAT = 1
ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LOCK = threading.RLock()
LAST_TEST = {}
REVISION = (None, "")
PRESETS = {"ollama": "http://127.0.0.1:11434/v1", "unsloth": "", "generic": ""}
ADAPTERS = ("openai-compatible", "unsloth-studio", "unsloth-agent-skills")
MAX_CONFIG = 16384


class LLMError(Exception):
    def __init__(self, code, say, status=None):
        super().__init__(say)
        self.code, self.say, self.status = code, say, status


def text(value, limit, label, empty=False):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise LLMError("bad-config", "The %s is malformed or too long." % label)
    if not empty and not value.strip():
        raise LLMError("bad-config", "Enter the %s." % label)
    return value.strip()


def url(value):
    value = text(value, 2048, "endpoint URL")
    try:
        p = urllib.parse.urlsplit(value)
        port = p.port
        if (p.scheme not in ("http", "https") or not p.hostname or p.username is not None
                or p.password is not None or p.query or p.fragment or "\\" in value
                or any(c.isspace() for c in value) or (port is not None and not 1 <= port <= 65535)):
            raise ValueError()
        p.hostname.encode("idna")
    except (ValueError, UnicodeError):
        raise LLMError("bad-url", "Use an HTTP(S) endpoint URL without credentials, query or fragment.")
    return value.rstrip("/")


def share_link(value):
    """Import a Studio link as a local reference, never fetch or execute it.

    GPU, GGUF and KV-cache choices belong to Studio. Opening the retained
    link there is a deliberate action; run=1 never becomes an API call here.
    """
    value = text(value, 4096, "Unsloth settings link")
    try:
        p = urllib.parse.urlsplit(value)
        origin = url(urllib.parse.urlunsplit((p.scheme, p.netloc, "", "", "")))
        if p.path.rstrip("/") != "/chat" or not p.fragment.startswith("run?"):
            raise ValueError()
        q = urllib.parse.parse_qs(p.fragment[4:], strict_parsing=True)
        if q.get("v") != ["1"] or any(len(v) != 1 for v in q.values()):
            raise ValueError()
        model = text(q.get("model", [""])[0], 512, "model ID")
        variant = text(q.get("ggufVariant", [""])[0], 128, "GGUF variant", True)
        cache = text(q.get("kvCacheDtype", [""])[0], 128, "KV cache type", True)
        context = q.get("customContextLength", [None])[0]
        if context is not None and (not context.isdigit() or not 1 <= int(context) <= 1048576):
            raise ValueError()
        vision = q.get("disableVision", [None])[0]
        if vision not in (None, "true", "false"):
            raise ValueError()
    except (ValueError, LLMError):
        raise LLMError("bad-link", "Use a version 1 Unsloth Chat run-settings share link.")
    # Keep only understood public settings; never retain arbitrary link parameters.
    params = {"v": "1", "model": model, "ggufVariant": variant, "kvCacheDtype": cache}
    if context is not None:
        params["customContextLength"] = context
    if vision is not None:
        params["disableVision"] = vision
    safe = origin + "/chat?run=1#run?" + urllib.parse.urlencode(params)
    return {"base_url": origin + "/v1", "model_hint": model,
            "studio_link": safe, "gguf_variant": variant, "kv_cache_dtype": cache,
            "context_tokens": int(context) if context is not None else None,
            "disable_vision": vision != "false"}


def model_profile(link, name, base_url):
    if not isinstance(link, str):
        raise LLMError("bad-profile", "Enter a Studio profile link.")
    try:
        keys = set(urllib.parse.parse_qs(urllib.parse.urlsplit(link).fragment[4:]))
    except ValueError:
        keys = set()
    if keys - {"v", "model", "ggufVariant", "kvCacheDtype", "customContextLength", "disableVision"}:
        raise LLMError("bad-profile", "This link contains Studio options Parseh cannot apply. Use a link with model, GGUF, KV cache, context and vision settings only.")
    imported = share_link(link)
    if imported["base_url"] != base_url:
        raise LLMError("bad-profile", "A model profile must use the saved endpoint. Change the connection on the host first.")
    if not imported["gguf_variant"] or not imported["kv_cache_dtype"]:
        raise LLMError("bad-profile", "The profile link must specify the installed GGUF variant and KV cache type.")
    if imported["kv_cache_dtype"] not in ("f16", "bf16", "q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "iq4_nl", "f32"):
        raise LLMError("bad-profile", "This KV cache type is not supported.")
    if imported["context_tokens"] is not None and not 4096 <= imported["context_tokens"] <= 131072:
        raise LLMError("bad-profile", "Use a profile context length between 4096 and 131072 tokens.")
    ident = hashlib.sha256(imported["studio_link"].encode("utf-8")).hexdigest()[:16]
    return {"id": ident, "name": text(name, 100, "profile name"), "link": imported["studio_link"]}


def validate(raw):
    if not isinstance(raw, dict) or type(raw.get("format_version")) is not int or raw["format_version"] != STORE_FORMAT:
        raise LLMError("bad-config", "The LLM configuration version is not supported.")
    if set(raw) - {"format_version", "provider_preset", "adapter", "base_url", "selected_model", "api_key",
                   "timeout_seconds", "json_mode", "studio_link", "context_tokens", "key_action",
                   "model_profiles", "selected_profile", "pending_profile", "review_models"}:
        raise LLMError("bad-config", "The LLM configuration contains unknown settings.")
    if not isinstance(raw.get("provider_preset"), str) or raw["provider_preset"] not in PRESETS or raw.get("adapter", "openai-compatible") not in ADAPTERS:
        raise LLMError("bad-config", "Choose a supported LLM provider and adapter.")
    timeout = raw.get("timeout_seconds", 60)
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise LLMError("bad-config", "The timeout must be between 1 and 300 seconds.")
    context_tokens = raw.get("context_tokens", 8192)
    if type(context_tokens) is not int or not 4096 <= context_tokens <= 131072:
        raise LLMError("bad-config", "The context budget must be between 4096 and 131072 tokens.")
    key = raw.get("api_key")
    if key is not None:
        key = text(key, 4096, "API key")
        if not key.isascii():
            raise LLMError("bad-config", "The API key must contain ASCII characters.")
    mode = raw.get("json_mode", "auto")
    if mode not in ("auto", "supported", "unsupported"):
        raise LLMError("bad-config", "The JSON capability is not supported.")
    out = {"format_version": STORE_FORMAT, "adapter": raw.get("adapter", "openai-compatible"),
           "provider_preset": raw["provider_preset"], "base_url": url(raw.get("base_url")),
           "selected_model": text(raw.get("selected_model"), 512, "model ID"),
           "api_key": key, "timeout_seconds": timeout, "json_mode": mode,
           "context_tokens": context_tokens}
    if raw.get("studio_link"):
        out["studio_link"] = share_link(raw["studio_link"])["studio_link"]
    profiles = raw.get("model_profiles", [])
    if not isinstance(profiles, list) or len(profiles) > 8:
        raise LLMError("bad-profile", "Save up to eight model profiles.")
    cleaned, seen = [], set()
    for p in profiles:
        if not isinstance(p, dict) or set(p) != {"id", "name", "link"}:
            raise LLMError("bad-profile", "The saved model profiles are malformed.")
        item = model_profile(p["link"], p["name"], out["base_url"])
        if item["id"] != p["id"] or item["id"] in seen:
            raise LLMError("bad-profile", "The saved model profile IDs are invalid or repeated.")
        seen.add(item["id"]); cleaned.append(item)
    if cleaned:
        out["model_profiles"] = cleaned
    for key in ("selected_profile", "pending_profile"):
        if raw.get(key) is not None:
            if not isinstance(raw[key], str) or raw[key] not in seen:
                raise LLMError("bad-profile", "The selected model profile no longer exists.")
            out[key] = raw[key]
    tasks = raw.get("review_models", {})
    if not isinstance(tasks, dict) or set(tasks) - {"suspect", "full", "workspace"}:
        raise LLMError("bad-config", "Choose a model for a transcript review method.")
    if tasks:
        out["review_models"] = {}
    for task, setting in tasks.items():
        if not isinstance(setting, dict) or set(setting) != {"model_id", "profile_id"}:
            raise LLMError("bad-config", "The review model setting is malformed.")
        model = text(setting["model_id"], 512, "review model ID")
        profile = setting["profile_id"]
        if profile is not None:
            p = next((p for p in cleaned if p["id"] == profile), None)
            if p is None or share_link(p["link"])["model_hint"] != model:
                raise LLMError("bad-profile", "The review model profile no longer matches its saved model.")
        out["review_models"][task] = {"model_id": model, "profile_id": profile}
    return out


def path(root=None):
    return os.path.join(root or ROOT, "config", "llm.json")


def load(root=None):
    try:
        with open(path(root), "rb") as f:
            data = f.read(MAX_CONFIG + 1)
        if len(data) > MAX_CONFIG:
            return None
        return validate(json.loads(data))
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, LLMError):
        return None


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()


def revision(config):
    """Opaque session ID for the connection the person saw before sending text.

    Never expose the fingerprint of credentials, including weak custom keys.
    """
    global REVISION
    with LOCK:
        stamp = fingerprint(config)
        if REVISION[0] != stamp:
            REVISION = (stamp, secrets.token_urlsafe(24))
        return REVISION[1]


def view(root=None):
    c = load(root)
    if c is None:
        return {"configured": False, "has_api_key": False, "presets": PRESETS,
                "settings": "/settings/llm/"}
    import asrworkspace
    return dict({k: v for k, v in c.items() if k != "api_key"}, configured=True,
                workspace=asrworkspace.sandbox_status(),
                connection_id=revision(c),
                last_test=LAST_TEST.get(fingerprint(c)),
                has_api_key=bool(c["api_key"]), presets=PRESETS, settings="/settings/llm/")


def preview(body, root=None):
    """Host-only discovery draft, with explicit credential controls."""
    old = load(root) or {}
    action = body.get("key_action", "keep")
    if action not in ("keep", "replace", "clear"):
        raise LLMError("bad-config", "Choose whether to keep, replace or clear the API key.")
    return validate(dict(body, format_version=STORE_FORMAT,
                         selected_model=body.get("selected_model") or "__discovery__",
                         api_key=body.get("api_key") if action == "replace" else
                         old.get("api_key") if action == "keep" else None))


def record_test(config, result, root=None):
    import time
    with LOCK:
        c = load(root)
        if c != config:
            raise LLMError("settings-changed", "The LLM settings changed during the connection test.")
        if result.get("json_mode"):
            c["json_mode"] = result["json_mode"]
            _write(c, root)
        LAST_TEST[fingerprint(c)] = dict(result, at=time.time())
        return view(root)


def save(body, root=None):
    if not isinstance(body, dict):
        raise LLMError("bad-config", "The configuration must be an object.")
    allowed = {"provider_preset", "adapter", "base_url", "selected_model", "timeout_seconds",
               "key_action", "api_key", "studio_link", "context_tokens"}
    if set(body) - allowed:
        raise LLMError("bad-config", "The configuration contains unknown settings.")
    with LOCK:
        old = load(root) or {}
        action = body.get("key_action", "keep")
        if action not in ("keep", "replace", "clear") or (action != "replace" and body.get("api_key")):
            raise LLMError("bad-config", "Choose whether to keep, replace or clear the API key.")
        raw = dict(body, format_version=STORE_FORMAT,
                   api_key=body.get("api_key") if action == "replace" else
                   old.get("api_key") if action == "keep" else None)
        if url(body.get("base_url")) == old.get("base_url"):
            raw["model_profiles"] = old.get("model_profiles", [])
            raw["review_models"] = old.get("review_models", {})
        c = validate(raw)
        _write(c, root)
        return view(root)


def select_model(body, root=None):
    """Any admitted device may change only the model at the saved endpoint."""
    if not isinstance(body, dict) or set(body) != {"selected_model"}:
        raise LLMError("bad-config", "Model selection accepts only an exact model ID.")
    with LOCK:
        old = load(root)
        if old is None:
            raise LLMError("unconfigured", "Configure the endpoint on the Parseh host first.")
        c = dict(old, selected_model=body["selected_model"], json_mode="auto")
        c.pop("pending_profile", None); c.pop("selected_profile", None)
        c = validate(c)
        _write(c, root)
        return view(root)


def review_model(body, root=None):
    """Model-only feature choices from any admitted browser; no destinations."""
    if (not isinstance(body, dict) or set(body) != {"task", "model_id", "profile_id"}
            or body.get("task") not in ("suspect", "full", "workspace")):
        raise LLMError("bad-config", "Select a review task and a saved model/profile only.")
    with LOCK:
        c = load(root)
        if c is None:
            raise LLMError("unconfigured", "Configure the endpoint on the host first.")
        tasks = dict(c.get("review_models", {}))
        if not body["model_id"] and body["profile_id"] is None:
            tasks.pop(body["task"], None)
        else:
            tasks[body["task"]] = {"model_id": body["model_id"], "profile_id": body["profile_id"]}
        c["review_models"] = tasks
        _write(validate(c), root)
        return view(root)


def for_review(c, task):
    if task not in ("suspect", "full", "workspace"):
        raise LLMError("bad-review", "Choose a saved transcript review method.")
    if c.get("pending_profile"):
        raise LLMError("model-profile-pending", "The model load is unconfirmed. Load its saved profile again before review.")
    setting = c.get("review_models", {}).get(task)
    if setting and setting["profile_id"] and c.get("selected_profile") != setting["profile_id"]:
        raise LLMError("profile-required", "Load this review's saved model profile before sending text.")
    return dict(c, selected_model=setting["model_id"] if setting else c["selected_model"])


def _write(c, root=None):
    encoded = json.dumps(c, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_CONFIG:
        raise LLMError("bad-config", "The saved settings are too large. Remove a model profile or shorten its link.")
    target = path(root)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(encoded.decode("utf-8"))
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def reset(root=None):
    with LOCK:
        try:
            os.unlink(path(root))
        except FileNotFoundError:
            pass
    return view(root)
