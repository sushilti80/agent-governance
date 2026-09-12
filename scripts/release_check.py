#!/usr/bin/env python3
"""Validate that a governance release tag matches the canonical release contract."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION_RE = re.compile(r"^20[0-9]{2}\.(0[1-9]|1[0-2])\.[0-9]+$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    version_path = root / "VERSION"
    if not version_path.is_file():
        print("FAIL: VERSION is missing")
        return 1

    version = version_path.read_text(encoding="utf-8").strip()
    if not VERSION_RE.fullmatch(version):
        print(f"FAIL: invalid VERSION format: {version!r}")
        return 1

    expected_tag = f"v{version}"
    if args.tag != expected_tag:
        print(f"FAIL: release tag {args.tag!r} does not match canonical {expected_tag!r}")
        return 1

    changelog = root / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
    if not re.search(rf"^## \[{re.escape(version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$", text, re.MULTILINE):
        print(f"FAIL: CHANGELOG.md has no dated release entry for {version}")
        return 1

    print(f"PASS: release tag {args.tag} matches VERSION and CHANGELOG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
