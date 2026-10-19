#!/usr/bin/env python3
"""Detect mapped prose, source and binary asset changes; never infer semantic equality."""
import argparse
import json
from pathlib import Path
import sys

from design_sync import SyncError, atomic, digest, encode, load_json, scoped


def scan(manifest, acknowledge=False):
    path = Path(manifest).resolve()
    root = path.parent
    raw = path.read_bytes()
    cfg = load_json(raw)
    if cfg.get("version") != 1 or not cfg.get("features"):
        raise SyncError("Links require version=1 and nonempty features")
    seen, hashes, features = set(), {}, []
    for feature in cfg["features"]:
        fid = feature["id"]
        if fid in seen or not feature.get("files") or not feature.get("acceptance"):
            raise SyncError("Each unique feature needs files and acceptance criteria")
        seen.add(fid)
        for name in feature["files"]:
            source = scoped(root, name)
            hashes[name] = digest(source.read_bytes()) if source.is_file() else None
            if hashes[name] is None and acknowledge:
                raise SyncError(f"Missing mapped file cannot be acknowledged: {name}")
        features.append(feature)
    state = root / ".design-sync" / "semantic-state.json"
    current = {"manifest_hash": digest(raw), "files": hashes}
    if acknowledge:
        atomic(state, encode(current))
        return {"status": "acknowledged", "note": "Agent reviewed linked artifacts; this is not proof of gameplay correctness"}, 0
    if not state.exists():
        return {"status": "needs-agent", "reason": "No reviewed semantic baseline", "features": features}, 1
    old = load_json(state.read_bytes())
    changed = sorted(name for name in set(hashes) | set(old["files"]) if hashes.get(name) != old["files"].get(name) or hashes.get(name) is None)
    affected = [feature for feature in features if set(feature["files"]) & set(changed)]
    mapping_changed = current["manifest_hash"] != old["manifest_hash"]
    return {"status": "needs-agent" if changed or mapping_changed else "clean",
            "changed_files": changed, "mapping_changed": mapping_changed,
            "features": features if mapping_changed else affected}, 1 if changed or mapping_changed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "acknowledge"))
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        report, code = scan(args.manifest, args.command == "acknowledge")
    except (SyncError, OSError, ValueError, KeyError, TypeError) as exc:
        report, code = {"status": "error", "error": str(exc)}, 3
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
