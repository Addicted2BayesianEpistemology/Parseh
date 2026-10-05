# SPDX-License-Identifier: GPL-3.0-or-later
"""The single, offline Whisper catalogue used by installers, jobs and workers.

Only entries with a pinned complete CTranslate2 package are installable. Source
checkpoints and conversions are separate identities: an equally named community
conversion is not silently substituted for an unverified checkpoint. Hashes
verify package bytes; ``fully_compatible`` additionally requires an audio/timing
qualification report. Conversion dependencies belong to maintainer tooling,
never to Parseh's server or installed speech worker.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "speechmodels.json"
FORMAT_VERSION = 1
DEFAULT_MODEL = "large-v3-turbo"
STANDARD_MODELS = ("large-v3-turbo", "large-v3")
_REVISION = re.compile(r"[a-f0-9]{40}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_NAME = re.compile(r"[a-z0-9][a-z0-9.-]{0,79}\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_REQUIRED = frozenset(("config.json", "model.bin", "tokenizer.json",
                       "preprocessor_config.json", "vocabulary.json"))


class CatalogueError(ValueError):
    """An invalid catalogue, incomplete package, or unsupported model."""


def validate_manifest(document):
    if not isinstance(document, dict) or document.get("format_version") != FORMAT_VERSION:
        raise CatalogueError("The Whisper model catalogue has an unsupported format.")
    rows = document.get("models")
    if not isinstance(rows, list) or not rows:
        raise CatalogueError("The Whisper model catalogue is empty.")
    seen = set()
    for row in rows:
        model = row.get("id") if isinstance(row, dict) else None
        if not isinstance(model, str) or not _NAME.fullmatch(model) or model in seen:
            raise CatalogueError("The Whisper model catalogue contains an invalid identifier.")
        seen.add(model)
        if not isinstance(row.get("source"), str) or not _REPOSITORY.fullmatch(row["source"]):
            raise CatalogueError("A Whisper source repository is invalid.")
        if not isinstance(row.get("revision"), str) or not _REVISION.fullmatch(row["revision"]):
            raise CatalogueError("A Whisper source revision is not pinned.")
        languages = row.get("languages")
        if not isinstance(languages, list) or any(not isinstance(x, str) or
                not re.fullmatch(r"[a-z]{2,3}", x) for x in languages):
            raise CatalogueError("A Whisper model has invalid language restrictions.")
        architecture = row.get("architecture", {})
        for key in ("encoder_layers", "decoder_layers", "decoder_attention_heads",
                    "d_model", "num_mel_bins"):
            value = architecture.get(key)
            if type(value) is not int or value <= 0:
                raise CatalogueError("A Whisper model has no complete architecture record.")
        profile = row.get("decoding", {})
        if (profile.get("task") != "transcribe" or profile.get("temperature") != 0 or
                type(profile.get("beam_size")) is not int or profile["beam_size"] < 1 or
                type(profile.get("condition_on_previous_text")) is not bool):
            raise CatalogueError("A Whisper model has an invalid decoding profile.")
        package = row.get("package")
        if package is None:
            if not row.get("availability_reason"):
                raise CatalogueError("An unavailable Whisper package needs an explanation.")
            continue
        if (not isinstance(package, dict) or not isinstance(package.get("revision"), str) or
                not _REVISION.fullmatch(package["revision"])):
            raise CatalogueError("A Whisper package revision is not pinned.")
        if not isinstance(package.get("repo"), str) or not _REPOSITORY.fullmatch(package["repo"]):
            raise CatalogueError("A Whisper package repository is invalid.")
        files = package.get("files", {})
        if not isinstance(files, dict) or not _REQUIRED.issubset(files):
            raise CatalogueError("A Whisper package lacks required offline assets.")
        for name, pin in files.items():
            if (not isinstance(name, str) or Path(name).name != name or "\\" in name or
                    name in (".", "..")):
                raise CatalogueError("A Whisper package has an unsafe file name.")
            if (not isinstance(pin, dict) or not isinstance(pin.get("sha256"), str) or
                    not _DIGEST.fullmatch(pin["sha256"]) or
                    type(pin.get("size")) is not int or pin["size"] < 1):
                raise CatalogueError("A Whisper package file is not hash-pinned.")
            bundled = pin.get("bundled")
            if bundled is not None and (not isinstance(bundled, str) or
                    Path(bundled).name != bundled or "\\" in bundled):
                raise CatalogueError("A bundled Whisper asset has an unsafe file name.")
        for location in package.get("file_sources", {}).values():
            if (not isinstance(location, dict) or not isinstance(location.get("revision"), str) or
                    not _REVISION.fullmatch(location["revision"])):
                raise CatalogueError("A Whisper supporting asset revision is not pinned.")
            if not isinstance(location.get("repo"), str) or not _REPOSITORY.fullmatch(location["repo"]):
                raise CatalogueError("A Whisper supporting asset repository is invalid.")
            remote = location.get("file")
            if (not isinstance(remote, str) or remote.startswith("/") or "\\" in remote or
                    ".." in remote.split("/")):
                raise CatalogueError("A Whisper supporting asset has an unsafe path.")
        if package.get("distribution") == "local-package":
            archive = package.get("package_name")
            if (not isinstance(archive, str) or Path(archive).name != archive or "\\" in archive or
                    not archive.endswith(".zip") or
                    not isinstance(package.get("package_sha256"), str) or
                    not _DIGEST.fullmatch(package["package_sha256"]) or
                    type(package.get("package_size")) is not int or package["package_size"] < 1):
                raise CatalogueError("A local Whisper package archive is not safely pinned.")
    if not set(STANDARD_MODELS).issubset(seen):
        raise CatalogueError("The standard Whisper models must remain available.")
    return document


with MANIFEST_PATH.open(encoding="utf-8") as _stream:
    _DOCUMENT = validate_manifest(json.load(_stream))
_ROWS = {row["id"]: row for row in _DOCUMENT["models"]}
MODELS = tuple(_ROWS)
ALLOWED_MODELS = frozenset(MODELS)
MODEL_PINS = {}
MODEL_INFO = {}
for _model, _row in _ROWS.items():
    _package = _row.get("package")
    if _package:
        _pin = deepcopy(_package)
        _pin["files"] = {name: (value["sha256"], value["size"])
                         for name, value in _package["files"].items()}
        MODEL_PINS[_model] = _pin
    _info = {key: deepcopy(value) for key, value in _row.items()
             if key not in ("package", "conversion")}
    _info.update(available=bool(_package),
                 package_revision=_package["revision"] if _package else None,
                 download=sum(pin["size"] for pin in _package["files"].values()) if _package else None,
                 package_licence=_package.get("licence") if _package else None,
                 availability_reason=_row.get("availability_reason"),
                 why=_row.get("availability_reason"))
    if _package:
        _info.update({key: _package.get(key) for key in
                      ("distribution", "package_name", "package_sha256", "package_size")})
    MODEL_INFO[_model] = _info


def entry(model):
    try:
        return deepcopy(_ROWS[model])
    except (KeyError, TypeError):
        raise CatalogueError("Choose a Whisper model from Speech to text settings.") from None


def installable(model):
    return isinstance(model, str) and model in MODEL_PINS


def compatible(model, language):
    row = _ROWS.get(model) if isinstance(model, str) else None
    return bool(row and (not row["languages"] or language in row["languages"]))


def choices(language=None):
    """Catalogue IDs; always include the standard multilingual choices."""
    return tuple(model for model in MODELS if language is None or compatible(model, language))


def decoding(model, *, second_pass=False):
    profile = deepcopy(entry(model)["decoding"])
    if second_pass:
        # Independent rechecks deliberately override language-specific first-pass
        # defaults. No transcript prompt or previous-text conditioning.
        profile.update(beam_size=10, temperature=0, condition_on_previous_text=False,
                       word_timestamps=True, task="transcribe")
    return profile


def provenance(model):
    row = entry(model)
    package = row.get("package")
    return {"model": model, "source": row["source"], "source_revision": row["revision"],
            "package": package["repo"] if package else None,
            "package_revision": package["revision"] if package else None,
            "licence": row["licence"], "package_licence": package.get("licence") if package else None,
            "compatibility": row["compatibility"], "fully_compatible": row["fully_compatible"],
            "alignment_repair": deepcopy(package.get("alignment_repair")) if package else None}


def bundled_file(model, name):
    row = entry(model)
    package = row.get("package")
    if not package or name not in package["files"]:
        raise CatalogueError("This Whisper package has no such file.")
    bundled = package["files"][name].get("bundled")
    return HERE / "speechmodel-assets" / bundled if bundled else None


def file_url(model, name):
    row = entry(model)
    package = row.get("package")
    if not package or name not in package["files"]:
        raise CatalogueError("This Whisper package has no such file.")
    if package.get("distribution") == "local-package" or package["files"][name].get("bundled"):
        return None
    location = package.get("file_sources", {}).get(name, {})
    repository = location.get("repo", package["repo"])
    revision = location.get("revision", package["revision"])
    path = location.get("file", name)
    return "https://huggingface.co/%s/resolve/%s/%s" % (
        quote(repository, safe="/"), revision, quote(path, safe="/"))


def packaged_file(model, name, package_root):
    """Resolve a prepared local package inside an explicitly selected host root.

    The caller still checks the returned file's pinned size and checksum. It
    must not accept arbitrary paths or catalogue entries from a browser.
    """
    row = entry(model)
    package = row.get("package")
    if not package or package.get("distribution") != "local-package" or name not in package["files"]:
        return None
    return Path(package_root) / model / package["revision"] / name


def _json_asset(folder, name):
    path = Path(folder) / name
    if not path.is_file() or path.stat().st_size > 16 << 20:
        raise CatalogueError("A Whisper package has a missing or oversized " + name + ".")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise CatalogueError("A Whisper package has an unreadable " + name + ".") from None


def validate_assets(model, folder, *, checksums=False):
    """Check offline assets, lexical IDs, mel dimensions and valid alignment heads.

    This is a structural check. A real CTranslate2 load and reference-audio
    qualification are separate checks and must never be inferred from this.
    """
    row = entry(model)
    package = row.get("package")
    if not package:
        raise CatalogueError(row["availability_reason"])
    for name, pin in package["files"].items():
        path = Path(folder) / name
        if not path.is_file() or path.stat().st_size != pin["size"]:
            raise CatalogueError("A Whisper package file is missing or incomplete: " + name + ".")
        if checksums:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
            if digest.hexdigest() != pin["sha256"]:
                raise CatalogueError("A Whisper package checksum does not match: " + name + ".")
    config = _json_asset(folder, "config.json")
    if not isinstance(config, dict):
        raise CatalogueError("The Whisper model configuration has an unsupported format.")
    architecture = row["architecture"]
    heads = config.get("alignment_heads")
    if not isinstance(heads, list) or not heads:
        raise CatalogueError("The Whisper package lacks word-alignment heads.")
    for head in heads:
        if (not isinstance(head, list) or len(head) != 2 or
                any(type(value) is not int for value in head) or
                not 0 <= head[0] < architecture["decoder_layers"] or
                not 0 <= head[1] < architecture["decoder_attention_heads"]):
            raise CatalogueError("The Whisper package has invalid word-alignment heads.")
    processor = _json_asset(folder, "preprocessor_config.json")
    if (not isinstance(processor, dict) or processor.get("sampling_rate") != 16000 or
            processor.get("feature_size") != architecture["num_mel_bins"] or
            processor.get("hop_length") != 160 or processor.get("n_fft") != 400):
        raise CatalogueError("The Whisper audio preprocessor does not match the model.")
    tokenizer = _json_asset(folder, "tokenizer.json")
    vocabulary = _json_asset(folder, "vocabulary.json")
    if not isinstance(tokenizer, dict) or not isinstance(tokenizer.get("model"), dict):
        raise CatalogueError("The Whisper tokenizer has an unsupported format.")
    model_vocab = tokenizer["model"].get("vocab")
    added = tokenizer.get("added_tokens")
    if not isinstance(model_vocab, dict) or not isinstance(added, list) or not isinstance(vocabulary, list):
        raise CatalogueError("The Whisper tokenizer or vocabulary has an unsupported format.")
    ids = dict(model_vocab)
    if any(not isinstance(token, str) or type(index) is not int or index < 0 for token, index in ids.items()):
        raise CatalogueError("The Whisper tokenizer has invalid vocabulary entries.")
    for token in added:
        if not isinstance(token, dict) or not isinstance(token.get("content"), str) or type(token.get("id")) is not int:
            raise CatalogueError("The Whisper tokenizer has malformed added tokens.")
        if token["content"] in ids and ids[token["content"]] != token["id"]:
            raise CatalogueError("The Whisper tokenizer has inconsistent token IDs.")
        ids[token["content"]] = token["id"]
    if any(not isinstance(token, str) or ids.get(token) != index
           for index, token in enumerate(vocabulary)):
        raise CatalogueError("The Whisper tokenizer and model vocabulary do not match.")
    if len(ids) != len(vocabulary) or set(ids.values()) != set(range(len(vocabulary))):
        raise CatalogueError("The Whisper tokenizer includes tokens absent from the model vocabulary.")
    required_tokens = ("<|startoftranscript|>", "<|transcribe|>", "<|endoftext|>", "<|0.00|>")
    if any(token not in ids for token in required_tokens):
        raise CatalogueError("The Whisper package lacks transcription or timestamp tokens.")
    for language in row["languages"]:
        if "<|" + language + "|>" not in ids:
            raise CatalogueError("The Whisper tokenizer lacks the selected language.")
    return {"model": model, "structural_assets": "verified", "fully_compatible": row["fully_compatible"],
            "vocabulary_size": len(vocabulary), "decoder_layers": architecture["decoder_layers"]}
