#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What this computer can run speech to text on, found out in a child.

    python3 lib/sttprobe.py         one line of JSON

lib/getstt.py runs this as a child of the server, with the Parseh python and
PYTHONPATH on the speech program's folder when there is one, and reads its
line.  A CHILD, because the questions below go to a graphics driver, and a
driver that goes wrong aborts the interpreter that asked: it must take this
process with it and not the server.  THE MODEL IS NEVER LOADED (that is one to
three gigabytes to answer a yes-or-no question); the whole look takes about
0.2 seconds.

WHAT COUNTS AS PROOF.  Counting CUDA devices is not enough.  With cuBLAS
missing, CTranslate2 still counts one device, lists half-precision types for it
and even loads the model -- and fails later, inside the first segment, with
"Library libcublas.so.12 is not found".  So this asks the three things
separately and lets lib/getstt.py decide:

  ct2 / cuda_devices / cuda_types    what the program itself sees (absent when the
                                     program is not installed yet)
  cublas                             whether cuBLAS for CUDA 12 LOADS: by its name,
                                     as CTranslate2 will ask for it, and failing
                                     that from the folders a CUDA toolkit lives
                                     in (which lib/getstt.py then hands to the
                                     worker, so the two agree)
  smi                                the card's name and memory from nvidia-smi
                                     -- cosmetic, and never taken for proof

Standard library only, on any Python 3.8 or newer: it runs before the program
exists, to say what is missing.
"""
import ctypes
import glob
import json
import os
import subprocess
import sys
import time

NAME = "cublas64_12.dll" if os.name == "nt" else "libcublas.so.12"


def candidate_dirs():
    """Where a CUDA 12 toolkit puts cuBLAS, apart from where the loader
    already looks: a few usual places, and every folder on the library path."""
    dirs = []
    if os.name == "nt":
        dirs += [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        if os.environ.get("CUDA_PATH"):
            dirs.append(os.path.join(os.environ["CUDA_PATH"], "bin"))
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")):
            if base:
                dirs += sorted(glob.glob(os.path.join(base, "NVIDIA GPU Computing Toolkit",
                                                      "CUDA", "v12*", "bin")), reverse=True)
    else:
        dirs += [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        for pattern in ("/usr/local/cuda*/lib64", "/usr/local/cuda*/targets/*/lib",
                        "/opt/cuda*/lib64", "/usr/lib/x86_64-linux-gnu", "/usr/lib64",
                        "/usr/lib/wsl/lib"):
            dirs += sorted(glob.glob(pattern), reverse=True)
        for entry in sys.path:
            if entry and os.path.isdir(entry):
                dirs += glob.glob(os.path.join(entry, "nvidia", "cublas", "lib"))
    seen, out = set(), []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def find_cublas(scan=True):
    """{"loads": bool, "name", "dir": folder it was found in or None, "error"}."""
    try:
        (ctypes.WinDLL if os.name == "nt" else ctypes.CDLL)(NAME)
        return {"loads": True, "name": NAME, "dir": None}
    except OSError as e:
        first = str(e)
    if scan:
        for d in candidate_dirs():
            path = os.path.join(d, NAME)
            if not os.path.isfile(path):
                continue
            try:
                if os.name == "nt":
                    if hasattr(os, "add_dll_directory"):
                        os.add_dll_directory(d)
                    ctypes.WinDLL(path)
                else:
                    ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                return {"loads": True, "name": NAME, "dir": d}
            except OSError:
                continue
    return {"loads": False, "name": NAME, "dir": None, "error": first}


def _smi_paths():
    names = ["nvidia-smi"]
    if os.name == "nt":
        root = os.environ.get("SystemRoot") or r"C:\Windows"
        names += [os.path.join(root, "System32", "nvidia-smi.exe"),
                  os.path.join(os.environ.get("ProgramFiles") or r"C:\Program Files",
                               "NVIDIA Corporation", "NVSMI", "nvidia-smi.exe")]
    return names


def smi():
    """The first card nvidia-smi lists: name, memory (bytes), driver, compute
    capability -- or None where there is no nvidia-smi or no card."""
    for fields in ("name,memory.total,driver_version,compute_cap", "name,memory.total,driver_version"):
        for exe in _smi_paths():
            try:
                done = subprocess.run([exe, "--query-gpu=" + fields, "--format=csv,noheader,nounits"],
                                      capture_output=True, text=True, timeout=10,
                                      stdin=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError):
                continue
            if done.returncode != 0 or not done.stdout.strip():
                continue
            row = [c.strip() for c in done.stdout.strip().splitlines()[0].split(",")]
            try:
                memory = int(float(row[1])) * 1024 * 1024
            except (IndexError, ValueError):
                memory = None
            return {"name": row[0], "memory": memory,
                    "driver": row[2] if len(row) > 2 else None,
                    "compute_cap": row[3] if len(row) > 3 else None}
    return None


def main():
    t = time.time()
    out = {"python": "%d.%d" % sys.version_info[:2], "platform": sys.platform}
    try:
        import ctranslate2
        out["ct2"] = ctranslate2.__version__
        try:
            out["cuda_devices"] = int(ctranslate2.get_cuda_device_count())
        except Exception as e:                                # noqa: BLE001
            out["cuda_devices"] = 0
            out["cuda_error"] = "%s: %s" % (type(e).__name__, e)
        out["cuda_types"] = []
        if out["cuda_devices"]:
            try:
                out["cuda_types"] = sorted(ctranslate2.get_supported_compute_types("cuda"))
            except Exception as e:                            # noqa: BLE001
                out["cuda_error"] = "%s: %s" % (type(e).__name__, e)
        try:
            out["cpu_types"] = sorted(ctranslate2.get_supported_compute_types("cpu"))
        except Exception:                                     # noqa: BLE001
            out["cpu_types"] = []
    except Exception as e:                                    # noqa: BLE001
        # not installed yet, or installed for another Python: the card can
        # still be listed, and the program is the piece that is missing
        out["ct2"] = None
        out["ct2_error"] = "%s: %s" % (type(e).__name__, e)
    # lib/getstt.py SCAN_FOR_CUBLAS says whether the usual places are looked in
    out["cublas"] = find_cublas(scan="--no-scan" not in sys.argv)
    out["smi"] = smi()
    out["seconds"] = round(time.time() - t, 2)
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
