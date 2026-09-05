#!/usr/bin/env python3
"""Write data/providers.json from scripts/providers/registry.py.

Offline and deterministic, so both push paths (Mac and Actions) can run it and emit
identical bytes: no rebase conflict between the two writers, and no commit at all
unless the registry changed. That is also why the file carries no
`generated` timestamp, unlike every other file in data/.

Run from the repo root.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "providers"))
import registry


def main() -> int:
    out = pathlib.Path("data")
    out.mkdir(exist_ok=True)
    path = out / "providers.json"
    body = json.dumps({"providers": registry.frontend()},
                      ensure_ascii=False, indent=1) + "\n"
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if body == old:
        print(f"[providers] unchanged ({len(registry.PROVIDERS)} providers)")
        return 0
    path.write_text(body, encoding="utf-8")
    print(f"[providers] written ({len(registry.PROVIDERS)} providers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
