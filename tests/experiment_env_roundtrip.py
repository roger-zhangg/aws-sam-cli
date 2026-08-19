"""EXPERIMENT (fork only): does a secret-shaped value survive a GITHUB_ENV round-trip?

Reproduces the credential path without any AWS involvement: `--write` exports synthetic
values through the same `write_env` used for real credentials, `--verify` reads them back
from os.environ and compares bytes. Any case that differs identifies what mangles the
value, and on which platform/shell.

Usage:
    python tests/experiment_env_roundtrip.py --write
    python tests/experiment_env_roundtrip.py --verify --label "windows/bash"
"""

import argparse
import json
import os
import platform
import sys

# 40 chars each, matching real AWS secret length. Every case differs from CTRL only in the
# special character(s) under test, so a failure isolates one variable.
PAD = "0123456789ABCDEFGHIJKLMNOPQRSTU"
CASES = {
    "CTRL_ALNUM": "abcdefghi" + PAD,
    "LEAD_SLASH": "/bcdefghi" + PAD,
    "MID_SLASH": "abcd/fghi" + PAD,
    "TRAIL_SLASH": "abcdefghi" + PAD[:-1] + "/",
    "LEAD_PLUS": "+bcdefghi" + PAD,
    "MID_PLUS": "abcd+fghi" + PAD,
    "LEAD_PERCENT": "%bcdefghi" + PAD,
    "LEAD_DASH": "-bcdefghi" + PAD,
    "LEAD_EQUALS": "=bcdefghi" + PAD,
    # shell-expansion shapes: cmd %VAR%, powershell $env:, cmd delayed !VAR!, bash $VAR
    "CMD_VARLIKE": "ab%PATH%i" + PAD,
    "PS_VARLIKE": "ab$env:Pi" + PAD,
    "BANG_VARLIKE": "ab!PATH!i" + PAD,
    "DOLLAR_VARLIKE": "ab$PATHfi" + PAD,
    "BACKSLASH": "abcd\\fghi" + PAD,
    "TILDE_SLASH": "~/bcdefgh" + PAD,
    "DOUBLE_SLASH": "//cdefghi" + PAD,
    "TRAIL_SPACE": "abcdefghi" + PAD[:-1] + " ",
}

PREFIX = "PROBE_"


def write_env(name, value):
    """Byte-for-byte the same as tests/setup_testing_resources.py:write_env."""
    with open(os.environ["GITHUB_ENV"], "a") as f:
        f.write(f"{name}={value}\n")


def do_write():
    for name, value in CASES.items():
        write_env(PREFIX + name, value)
    print(f"wrote {len(CASES)} probe values via write_env()")
    print(f"writer: {platform.system()} {platform.release()} python {sys.version.split()[0]}")


def do_verify(label):
    print(f"\n{'='*74}\nVERIFY [{label}]  {platform.system()} python {sys.version.split()[0]}\n{'='*74}")
    print(f"{'case':16s} {'ok':4s} expected -> actual (repr, only when differing)")
    bad = {}
    for name, expected in CASES.items():
        actual = os.environ.get(PREFIX + name)
        ok = actual == expected
        if ok:
            print(f"{name:16s} PASS")
        else:
            bad[name] = {"expected": expected, "actual": actual}
            print(f"{name:16s} FAIL {expected!r}")
            print(f"{'':16s}      -> {actual!r}")
            if actual is not None:
                print(f"{'':16s}      exp_hex={expected.encode().hex()}")
                print(f"{'':16s}      act_hex={actual.encode().hex()}")
    print(f"\nRESULT [{label}]: {len(CASES)-len(bad)}/{len(CASES)} intact, {len(bad)} mangled")
    if bad:
        print("MANGLED_JSON " + json.dumps({"label": label, "cases": sorted(bad)}))
    return 0  # never fail the job; the report is the output


def do_sign(label):
    """Offline SigV4: same key + same frozen timestamp must give the same signature
    on every platform. Separates 'the env mangled the value' from 'the SDK signs
    special-character keys differently'. No AWS call, no real credentials."""
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials

    print(f"\n{'='*74}\nSIGV4 [{label}]  {platform.system()} python {sys.version.split()[0]}\n{'='*74}")
    for name, secret in CASES.items():
        req = AWSRequest(method="POST", url="https://sts.us-east-1.amazonaws.com/", data="Action=GetCallerIdentity")
        req.context["timestamp"] = "20260101T000000Z"
        SigV4Auth(Credentials("AKIAIOSFODNN7EXAMPLE", secret), "sts", "us-east-1").add_auth(req)
        sig = req.headers["Authorization"].split("Signature=")[-1]
        print(f"  {name:16s} {sig}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--sign", action="store_true")
    p.add_argument("--label", default="unknown")
    a = p.parse_args()
    if a.write:
        do_write()
    elif a.verify:
        sys.exit(do_verify(a.label))
    elif a.sign:
        do_sign(a.label)
    else:
        p.error("need --write, --verify or --sign")


if __name__ == "__main__":
    main()
