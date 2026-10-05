# SPDX-License-Identifier: GPL-3.0-or-later
"""Trusted resource limits inside the OS sandbox, before executing agent code.

This is NOT a Python sandbox. Isolation is supplied by bubblewrap: no host
home/configuration, network, process view or writable files except result.csv.
"""
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
code = sys.stdin.read(12001)
if len(code.encode("utf-8")) > 12000:
    raise SystemExit("Code exceeds the workspace limit.")
sys.path.insert(0, "/work")  # Read-only, feature-owned CSV helper in the sandbox.
exec(compile(code, "<workspace-code>", "exec"), {"__name__": "__main__"})
