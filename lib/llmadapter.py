# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable OpenAI-compatible text adapter; standard library only.

No redirects, proxy environment, server response bodies or secrets in errors.
An explicit deadline bounds each call including a slowly trickling response.
"""
import http.client
import json
import queue
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
        c = self.config
        p = urllib.parse.urlsplit(c["base_url"])
        conn_type = http.client.HTTPSConnection if p.scheme == "https" else http.client.HTTPConnection

        class CancellableConnection(conn_type):
            def connect(self):
                # DNS/connect can finish after the waiting caller cancelled.
                # Check again before any transcript bytes can be sent.
                cancel.check()
                super().connect()
                if cancel.event.is_set():
                    self.close()
                cancel.check()

        conn = CancellableConnection(p.hostname, p.port, timeout=c["timeout_seconds"])
        cancel.attach(conn)
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
                conn.request("GET" if body is None else "POST", target, body=body, headers=headers)
                response = conn.getresponse()
                if response.status != 200:
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
            cancel.check()
            left = deadline - time.monotonic()
            if left <= 0:
                cancel.cancel()
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

    def generate(self, messages, cancel=None, json_mode=None, max_tokens=2048):
        use_json = self.config.get("json_mode") != "unsupported" if json_mode is None else json_mode
        payload = {"model": self.config["selected_model"], "messages": messages,
                   "temperature": 0, "stream": False, "max_tokens": max_tokens}
        if use_json:
            payload["response_format"] = {"type": "json_object"}
        raw = self.request("chat/completions", payload, cancel)
        try:
            choice = raw["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") not in (None, "stop") or not isinstance(content, str):
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError):
            raise LLMError("invalid-response", "The endpoint returned an incomplete or invalid text response.")
        return parse_json(content)

    def test(self):
        """Tiny synthetic input only. Never claims recognition accuracy."""
        messages = [{"role": "system", "content": 'Return only the JSON object {"ok":true}.'},
                    {"role": "user", "content": 'Return the requested JSON object.'}]
        mode = "supported"
        try:
            raw = self.generate(messages, json_mode=True, max_tokens=64)
        except LLMError as e:
            if e.status not in (400, 422) or e.code != "http-error":
                raise
            raw = self.generate(messages, json_mode=False, max_tokens=64)
            mode = "unsupported"
        if raw != {"ok": True}:
            raise LLMError("structured-output", "The selected model did not return the requested JSON object.")
        return {"json_mode": mode, "say": "The selected model returned valid JSON. This does not test linguistic accuracy."}


def adapter(config):
    # Provider presets supply defaults, never distinct generation code.
    return OpenAICompatible(config)
