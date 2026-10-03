# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable OpenAI-compatible text adapter; standard library only.

No redirects, proxy environment, server response bodies or secrets in errors.
An explicit deadline bounds each call including a slowly trickling response.
"""
import http.client
import json
import queue
import re
import socket
import threading
import time
import urllib.parse

from llmconfig import LLMError, validate

MAX_RESPONSE = 256 * 1024
MAX_REQUEST = 64 * 1024
MAX_ERROR = 16 * 1024


class Cancellation:
    def __init__(self):
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.connection = None

    def attach(self, conn):
        with self.lock:
            self.connection = conn
            if self.event.is_set():
                self._close()

    def _close(self):
        conn = self.connection
        if conn is not None:
            try:
                if conn.sock:
                    conn.sock.shutdown(socket.SHUT_RDWR)
                conn.close()
            except OSError:
                pass

    def cancel(self):
        self.event.set()
        with self.lock:
            self._close()

    def check(self):
        if self.event.is_set():
            raise LLMError("cancelled", "LLM review was cancelled. The Whisper result is intact.")


def parse_json(content):
    try:
        return json.loads(content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise LLMError("invalid-json", "The endpoint returned invalid JSON. The Whisper result is intact.")


def endpoint_error(status, content=b""):
    """Map known endpoint failures to static sentences; never echo its body."""
    if status in (401, 403):
        return LLMError("authentication", "The endpoint refused authentication.", status)
    if status in (400, 404, 409, 422, 503) and len(content) <= MAX_ERROR:
        try:
            raw = parse_json(content)
            error = raw.get("error", raw.get("detail")) if isinstance(raw, dict) else None
            message = error.get("message") if isinstance(error, dict) else error
            code = error.get("code") if isinstance(error, dict) else None
            missing = code in ("model_not_loaded", "no_model_loaded")
            if isinstance(message, str):
                missing = missing or any(phrase in message.lower() for phrase in (
                    "no model loaded", "no model is loaded", "model is not loaded", "model not loaded"))
            if missing:
                return LLMError("model-not-loaded", "The endpoint has no model loaded. Load the selected model in its own interface, wait until it is ready, then retry.", status)
        except LLMError:
            pass
    return LLMError("http-error", "The endpoint refused the request (HTTP %d)." % status, status)


class OpenAICompatible:
    def __init__(self, config):
        self.config = validate(config)

    def request(self, route, payload=None, cancel=None):
        cancel = cancel or Cancellation()
        cancel.check()
        request_cancel = Cancellation()
        c = self.config
        p = urllib.parse.urlsplit(c["base_url"])
        conn_type = http.client.HTTPSConnection if p.scheme == "https" else http.client.HTTPConnection

        class CancellableConnection(conn_type):
            def connect(self):
                # DNS/connect can finish after the waiting caller cancelled.
                # Check again before any transcript bytes can be sent.
                cancel.check()
                request_cancel.check()
                super().connect()
                if cancel.event.is_set() or request_cancel.event.is_set():
                    self.close()
                cancel.check()
                request_cancel.check()

        conn = CancellableConnection(p.hostname, p.port, timeout=c["timeout_seconds"])
        request_cancel.attach(conn)
        target = p.path.rstrip("/") + "/" + route.lstrip("/")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if body is not None and len(body) > MAX_REQUEST:
            raise LLMError("too-large", "The LLM input window is too large.")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if c["api_key"]:
            headers["Authorization"] = "Bearer " + c["api_key"]
        result = queue.Queue(maxsize=1)

        def work():
            try:
                cancel.check()
                request_cancel.check()
                conn.request("GET" if body is None else "POST", target, body=body, headers=headers)
                response = conn.getresponse()
                if response.status not in (200, 201):
                    status = response.status
                    # Read only a small, bounded failure payload, solely to
                    # recognize static categories. It is never logged/returned.
                    failure = response.read(MAX_ERROR + 1) if status in (400, 404, 409, 422, 503) else b""
                    raise endpoint_error(status, failure)
                declared = response.getheader("Content-Length")
                if declared and (not declared.isdigit() or int(declared) > MAX_RESPONSE):
                    raise LLMError("too-large", "The endpoint response is too large.")
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise LLMError("too-large", "The endpoint response is too large.")
                result.put((True, parse_json(raw)))
            except LLMError as e:
                result.put((False, e))
            except Exception:
                result.put((False, LLMError("connection", "The endpoint could not be reached or read.")))
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True, name="llm-http").start()
        deadline = time.monotonic() + c["timeout_seconds"]
        while True:
            try:
                cancel.check()
            except LLMError:
                request_cancel.cancel()
                raise
            left = deadline - time.monotonic()
            if left <= 0:
                # A deadline aborts this request, not the whole review pass.
                request_cancel.cancel()
                raise LLMError("timeout", "The endpoint timed out. The Whisper result is intact.")
            try:
                ok, value = result.get(timeout=min(left, .1))
            except queue.Empty:
                continue
            cancel.check()
            if not ok:
                raise value
            return value

    def models(self, cancel=None):
        raw = self.request("models", cancel=cancel)
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list) or len(raw["data"]) > 2000:
            raise LLMError("models-unavailable", "Model discovery is unavailable. Enter the exact model ID.")
        models = []
        for item in raw["data"]:
            ident = item.get("id") if isinstance(item, dict) else None
            if not isinstance(ident, str) or not ident.strip() or len(ident) > 512 or any(ord(c) < 32 for c in ident):
                raise LLMError("models-unavailable", "The endpoint returned an invalid model list.")
            if ident not in models:
                models.append(ident)
        return models

    def _completion(self, messages, cancel, use_json, max_tokens, observe=None, extensions=None):
        if self.config.get("pending_profile"):
            raise LLMError("model-profile-pending", "The selected model profile has not finished loading. Apply it again or select the loaded model in LLM Integration.")
        payload = {"model": self.config["selected_model"], "messages": messages,
                   "temperature": 0, "stream": False, "max_tokens": max_tokens}
        if extensions:
            payload.update(extensions)
        if use_json:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        raw = self.request("chat/completions", payload, cancel)
        content, reasoning, finish = "", "", None
        try:
            choice = raw["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
            reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
            finish = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError, AttributeError):
            pass
        content = content if isinstance(content, str) else ""
        reasoning = reasoning if isinstance(reasoning, str) else ""
        embedded = re.findall(r"<think>(.*?)</think>", content, flags=re.S)
        answer = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
        if "<think>" in answer:
            reasoning += "\n" + answer.split("<think>", 1)[-1]
            answer = answer.split("<think>", 1)[0].strip()
        if embedded:
            reasoning += "\n" + "\n".join(embedded)

        def safe(value, limit):
            if not isinstance(value, str):
                return ""
            key = self.config.get("api_key")
            if key:
                value = value.replace(key, "[redacted credential]")
            return value[:limit]

        usage = raw.get("usage") if isinstance(raw, dict) else None
        trace = {"raw_answer": safe(content, 16384), "answer": safe(answer, 16384),
                 "reasoning": safe(reasoning.strip(), 16384), "finish_reason": safe(finish, 40),
                 "model": safe(raw.get("model", "") if isinstance(raw, dict) else "", 512),
                 "elapsed_seconds": round(time.monotonic() - started, 2),
                 "output_limit": max_tokens,
                 "response_clipped": len(content) > 16384 or len(reasoning) > 16384,
                 "usage": {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                           if isinstance(usage, dict) and type(usage.get(k)) is int and usage[k] >= 0}}
        if observe:
            observe(trace)
        if finish == "length":
            raise LLMError("output-limit", "The model reached its output limit before finishing the sentence. Inspect LLM responses for details.")
        if finish not in (None, "stop"):
            raise LLMError("invalid-response", "The model did not finish a normal text answer. Inspect LLM responses for details.")
        if not answer:
            raise LLMError("no-final-answer", "The model returned no final answer. Its reasoning, if supplied, is shown in LLM responses.")
        return answer

    def generate_text(self, messages, cancel=None, max_tokens=2048, observe=None, skill=None):
        """Plain final text, separately preserving bounded endpoint reasoning."""
        if skill:
            raise LLMError("skills-unavailable", "This adapter does not invoke installed skills. Choose the Unsloth Agent Skills adapter or use the short prompt.")
        return self._completion(messages, cancel, False, max_tokens, observe)

    def agent_turn(self, messages, tools, cancel=None, max_tokens=2048, observe=None):
        """One external tool turn. Parseh, rather than the endpoint, runs tools."""
        payload = {"model": self.config["selected_model"], "messages": messages,
                   "tools": tools, "tool_choice": "auto", "parallel_tool_calls": False,
                   "temperature": 0, "stream": False, "max_tokens": max_tokens}
        if self.config.get("pending_profile"):
            raise LLMError("model-profile-pending", "Finish loading this model profile before review.")
        if isinstance(self, UnslothStudio):
            # Explicit external functions; never enable Studio's host tools/MCP.
            payload.update(enable_thinking=True, enable_tools=False, mcp_enabled=False)
        started = time.monotonic()
        raw = self.request("chat/completions", payload, cancel)
        try:
            choice = raw["choices"][0]
            message = choice["message"]
            finish = choice.get("finish_reason")
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
            calls = message.get("tool_calls") or []
            if (not isinstance(content, str) or not isinstance(reasoning, str)
                    or not isinstance(calls, list) or len(calls) > 4):
                raise ValueError()
            cleaned, seen = [], set()
            allowed = {t["function"]["name"] for t in tools}
            for call in calls:
                ident, function = call["id"], call["function"]
                name, arguments = function["name"], function["arguments"]
                if (call.get("type") != "function" or not isinstance(ident, str)
                        or not re.fullmatch(r"[\w-]{1,200}", ident) or ident in seen
                        or name not in allowed or not isinstance(arguments, str)
                        or len(arguments.encode("utf-8")) > 12000
                        or not isinstance(parse_json(arguments), dict)):
                    raise ValueError()
                seen.add(ident)
                cleaned.append({"id": ident, "type": "function", "function": {"name": name, "arguments": arguments}})
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            raise LLMError("invalid-tools", "The model returned an invalid workspace tool call.")
        if observe:
            key = self.config.get("api_key")
            safe = lambda s: s.replace(key, "[redacted credential]") if key else s
            observe({"answer": safe(content)[:16000], "reasoning": safe(reasoning)[:16000],
                     "tool_calls": parse_json(safe(json.dumps(cleaned, ensure_ascii=False))),
                     "finish_reason": finish if finish in ("stop", "tool_calls", "length", None) else "other",
                     "elapsed_seconds": round(time.monotonic() - started, 2)})
        if finish == "length":
            raise LLMError("output-limit", "The model reached its reasoning or tool output limit. Retry the remaining words.")
        if finish not in ("stop", "tool_calls", None) or not calls:
            raise LLMError("tools-required", "This review needs a model that calls the provided workspace tools. Its text answer is available in LLM responses.")
        # Reasoning is diagnostic data, never injected as instructions/history.
        return {"role": "assistant", "content": content or None, "tool_calls": cleaned}

    def generate(self, messages, cancel=None, json_mode=None, max_tokens=2048):
        use_json = self.config.get("json_mode") != "unsupported" if json_mode is None else json_mode
        return parse_json(self._completion(messages, cancel, use_json, max_tokens))

    def test(self):
        """Tiny synthetic input only. Never claims recognition accuracy."""
        messages = [{"role": "system", "content": 'Reply only with: Parseh connection OK'},
                    {"role": "user", "content": 'Check the text connection.'}]
        raw = self.generate_text(messages, max_tokens=2048)
        if raw.strip().strip('"\' .') != "Parseh connection OK":
            raise LLMError("text-output", "The selected model did not return the short requested answer.")
        return {"say": "The selected model returned the requested text. This does not test linguistic accuracy."}


class UnslothStudio(OpenAICompatible):
    """Explicit native capability; presets never select execution code."""
    def _api(self):
        base = self.config["base_url"]
        if not base.endswith("/v1"):
            raise LLMError("studio-unavailable", "The Unsloth Studio adapter needs an API base URL ending in /v1.")
        transport = {k: v for k, v in self.config.items() if k not in ("model_profiles", "selected_profile", "pending_profile", "review_models")}
        return OpenAICompatible(dict(transport, base_url=base[:-3] + "/api"))

    def _completion(self, messages, cancel, use_json, max_tokens, observe=None, extensions=None):
        return super()._completion(messages, cancel, use_json, max_tokens, observe,
                                   dict({"enable_thinking": False}, **(extensions or {})))

    def resolve_profile(self, profile):
        """Read installed GGUFs and resolve one exact local file, never a Hub load."""
        from llmconfig import share_link
        info = share_link(profile["link"])
        api = self._api()
        rows = api.request("models/cached-gguf")
        cached = rows.get("cached") if isinstance(rows, dict) else None
        if not isinstance(cached, list) or len(cached) > 2000:
            raise LLMError("models-unavailable", "Unsloth's installed GGUF inventory is unavailable.")
        match = next((r for r in cached if isinstance(r, dict) and r.get("repo_id") == info["model_hint"]
                      and not r.get("partial") and r.get("task") in (None, "text-generation")), None)
        if match is None:
            raise LLMError("model-not-installed", "This profile's GGUF model is not fully installed in Unsloth. Install it there first.")
        query = urllib.parse.urlencode({"repo_id": info["model_hint"], "offline": "true", "prefer_local_cache": "true"})
        variants = api.request("models/gguf-variants?" + query)
        items = variants.get("variants") if isinstance(variants, dict) else None
        if not isinstance(items, list) or len(items) > 2000:
            raise LLMError("models-unavailable", "Unsloth's installed variant list is unavailable.")
        quant = next((r for r in items if isinstance(r, dict) and r.get("quant") == info["gguf_variant"]
                      and r.get("downloaded") is True and not r.get("partial")), None)
        if quant is None:
            raise LLMError("variant-not-installed", "This GGUF variant is not fully installed. Choose an installed variant in the profile link.")
        if not info["disable_vision"] and match.get("has_vision") and variants.get("dependencies_resolved") is not True:
            raise LLMError("vision-unavailable", "This profile's vision dependencies cannot be verified as installed. Use a text-only Studio link with disableVision=true.")
        query = urllib.parse.urlencode({"repo_id": info["model_hint"], "variant": info["gguf_variant"]})
        located = api.request("models/cached-model-path?" + query)
        local = located.get("path") if isinstance(located, dict) else None
        if (not isinstance(local, str) or len(local) > 4096 or any(ord(c) < 32 for c in local)
                or located.get("is_dir") is not False or not local.lower().endswith(".gguf")
                or not (local.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:[\\\\/]", local))):
            raise LLMError("model-path-unavailable", "Unsloth could not resolve this variant to an installed GGUF file.")
        return info, local

    def load_profile(self, info, local):
        payload = {"model_path": local, "gguf_variant": info["gguf_variant"],
                   "cache_type_kv": info["kv_cache_dtype"], "disable_vision": info["disable_vision"],
                   "trust_remote_code": False, "speculative_type": "off"}
        if info["context_tokens"] is not None:
            payload["max_seq_length"] = info["context_tokens"]
        api = self._api()
        loaded = api.request("inference/load", payload)
        if not isinstance(loaded, dict) or loaded.get("status") not in ("success", "loaded", "already_loaded"):
            raise LLMError("model-load-failed", "Unsloth did not confirm loading the selected profile. Check Studio and retry.")
        state = api.request("inference/status")
        if (not isinstance(state, dict) or state.get("loading") or not state.get("loaded")
                or (state.get("model_identifier") not in (local, info["model_hint"])
                    and state.get("active_model") != info["model_hint"])
                or state.get("gguf_variant") != info["gguf_variant"]
                or state.get("cache_type_kv") != info["kv_cache_dtype"]
                or state.get("disable_vision") is not info["disable_vision"]):
            raise LLMError("model-load-unverified", "The endpoint's loaded model or options do not match the profile. Check Studio and retry.")
        actual = state.get("context_length")
        if type(actual) is not int or not 4096 <= actual <= 131072:
            raise LLMError("model-context", "The loaded context length is outside Parseh's supported budget. Adjust it in Studio and retry.")
        # Verify the public ID as well; local file paths never leave this adapter.
        models = self.request("models")
        if not isinstance(models, dict) or not isinstance(models.get("data"), list) or not any(
                isinstance(r, dict) and r.get("id") == info["model_hint"] and r.get("loaded") is True
                for r in models["data"]):
            raise LLMError("model-load-unverified", "Unsloth did not advertise the loaded profile under its model ID. Check Studio and retry.")
        return {"context_tokens": actual, "gguf_variant": info["gguf_variant"],
                "kv_cache_dtype": info["kv_cache_dtype"], "disable_vision": info["disable_vision"],
                "context_adjusted": info["context_tokens"] is not None and actual != info["context_tokens"]}


class UnslothAgentSkills(UnslothStudio):
    """Opt-in native skills, sharing transport and final-text validation."""
    def _skills(self):
        return self._api()

    def skill_status(self, name, cancel=None):
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise LLMError("invalid-skill", "The skill name is invalid.")
        rows = self._skills().request("skills", cancel=cancel)
        if not isinstance(rows, list) or len(rows) > 3000:
            raise LLMError("skills-unavailable", "The endpoint returned an invalid skill catalog.")
        found = next((r for r in rows if isinstance(r, dict) and r.get("name") == name and not r.get("shadowed")), None)
        return {"supported": True, "installed": found is not None,
                "ready": bool(found and found.get("enabled") is True and found.get("valid") is True)}

    def install_skill(self, name, description, instructions):
        if self.skill_status(name)["installed"]:
            raise LLMError("skill-exists", "This skill is already installed. Inspect or enable it in Unsloth Studio; Parseh will not overwrite it.")
        self._skills().request("skills", {"name": name, "description": description, "instructions": instructions})
        return self.skill_status(name)

    def generate_text(self, messages, cancel=None, max_tokens=2048, observe=None, skill=None):
        if not skill:
            return super().generate_text(messages, cancel, max_tokens, observe)
        if not self.skill_status(skill, cancel)["ready"]:
            raise LLMError("skill-unavailable", "Install and enable the correction skill in Unsloth Studio, then retry or use the short prompt.")
        return self._completion(messages, cancel, False, max_tokens, observe,
                                {"enable_tools": True, "enabled_tools": ["read_skill"], "mcp_enabled": False})


def adapter(config):
    # Provider presets supply defaults, never distinct generation code.
    kind = {"unsloth-agent-skills": UnslothAgentSkills, "unsloth-studio": UnslothStudio}.get(config.get("adapter"), OpenAICompatible)
    return kind(config)
