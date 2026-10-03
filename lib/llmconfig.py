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
ADAPTERS = ("openai-compatible", "unsloth-agent-skills")
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
        vision = q.get("disableVision", [None])[0]
        if vision not in (None, "true", "false"):
            raise ValueError()
    except (ValueError, LLMError):
        raise LLMError("bad-link", "Use a version 1 Unsloth Chat run-settings share link.")
    # Keep only understood public settings; never retain arbitrary link parameters.
    params = {"v": "1", "model": model, "ggufVariant": variant, "kvCacheDtype": cache}
    if vision is not None:
        params["disableVision"] = vision
    safe = origin + "/chat?run=1#run?" + urllib.parse.urlencode(params)
    return {"base_url": origin + "/v1", "model_hint": model,
            "studio_link": safe, "gguf_variant": variant, "kv_cache_dtype": cache}


def validate(raw):
    if not isinstance(raw, dict) or type(raw.get("format_version")) is not int or raw["format_version"] != STORE_FORMAT:
        raise LLMError("bad-config", "The LLM configuration version is not supported.")
    if set(raw) - {"format_version", "provider_preset", "adapter", "base_url", "selected_model", "api_key",
                   "timeout_seconds", "json_mode", "studio_link", "context_tokens", "key_action"}:
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
    return dict({k: v for k, v in c.items() if k != "api_key"}, configured=True,
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
        c = validate(dict(old, selected_model=body["selected_model"], json_mode="auto"))
        _write(c, root)
        return view(root)


def _write(c, root=None):
    target = path(root)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)
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
