#!/usr/bin/env python3
"""Launch a one-shot UE editor process to pull/push existing /Game DataTables."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

from design_sync import SyncError, atomic, digest, encode, load_json, restore, scoped, snapshots


def execute(args):
    project = Path(args.project).resolve()
    root = project.parent
    engine = Path(args.engine).resolve()
    if project.suffix != ".uproject" or not project.is_file() or not engine.is_file():
        raise SyncError("Provide an existing .uproject and UnrealEditor-Cmd executable")
    bindings = load_json(Path(args.bindings).resolve().read_bytes())
    if bindings.get("version") != 1 or not bindings.get("tables"):
        raise SyncError("Bindings need version=1 and tables")
    paths, asset_paths, seen_sources, seen_assets, tables = set(), set(), set(), set(), []
    for entry in bindings["tables"]:
        asset = entry["asset"]
        if not asset.startswith("/Game/") or "." in asset or ".." in asset or asset in seen_assets:
            raise SyncError("Use distinct /Game/... package paths, without object suffix")
        seen_assets.add(asset)
        source = scoped(root, entry["json"])
        if source in seen_sources:
            raise SyncError("Duplicate JSON output")
        seen_sources.add(source)
        if source.suffix.lower() != ".json" or ".design-sync" in source.relative_to(root).parts:
            raise SyncError("JSON must be a project data file outside .design-sync")
        paths.add(source)
        uasset = scoped(root, "Content/" + asset[len("/Game/"):] + ".uasset")
        if not uasset.is_file():
            raise SyncError(f"Asset file missing: {uasset}; create DataTable with correct row struct first")
        for suffix in (".uasset", ".uexp", ".ubulk"):
            paths.add(uasset.with_suffix(suffix))
            asset_paths.add(uasset.with_suffix(suffix))
        if args.command == "push" and not source.is_file():
            raise SyncError(f"Source missing: {source}")
        tables.append({"asset": asset, "source": str(source)})
    state_dir = root / ".design-sync"
    state_dir.mkdir(exist_ok=True)
    lock = state_dir / "ue-bridge.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as exc:
        raise SyncError("UE bridge already running; inspect a stale lock before removing it") from exc
    before, written = None, set()
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        before = snapshots(root, paths)
        with tempfile.TemporaryDirectory(prefix="gds-ue-", dir=state_dir) as temporary:
            request_path = Path(temporary) / "request.json"
            token = uuid.uuid4().hex
            for index, table in enumerate(tables):
                table["staged"] = str(Path(temporary) / f"table-{index}.json")
            atomic(request_path, encode({"mode": args.command, "token": token, "tables": tables}))
            env = dict(os.environ, GDS_UE_REQUEST=str(request_path))
            script = Path(__file__).with_name("ue_editor_bridge.py")
            result = subprocess.run([str(engine), str(project), "-run=pythonscript", f"-script={script}",
                                     "-unattended", "-nullrhi", "-nosplash", "-stdout", "-FullStdOutLogOutput"],
                                    cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    timeout=args.timeout, shell=False)
            receipt_path = Path(str(request_path) + ".result.json")
            receipt = load_json(receipt_path.read_bytes()) if receipt_path.exists() else {}
            if result.returncode or receipt.get("token") != token or not receipt.get("success"):
                raise SyncError(f"UE operation failed: {receipt.get('error', 'missing success receipt')}; {result.stdout[-6000:]} {result.stderr[-2000:]}")
            # A bridge run never overwrites a file saved by another editor in the meantime.
            for table in tables:
                name = str(Path(table["source"]).relative_to(root))
                current = snapshots(root, [Path(table["source"])])[name]
                if current != before[name]:
                    raise SyncError("JSON changed while UE was running; rerun after resolving concurrent edits")
            if args.command == "pull":
                state_path = state_dir / "state.json"
                recorded = load_json(state_path.read_bytes()).get("view_hashes", {}) if state_path.exists() else {}
                # First validate every target, then write the whole batch.
                for table in tables:
                    target = Path(table["source"])
                    staged = Path(table["staged"]).read_bytes()
                    if target.exists() and load_json(target.read_bytes()) != load_json(staged):
                        name = next((n for n in recorded if scoped(root, n) == target), None)
                        if name is None or digest(target.read_bytes()) != recorded[name]:
                            raise SyncError("Pull would overwrite unbaselined or locally edited JSON; export to a new temporary JSON path and merge explicitly")
                for table in tables:
                    target = Path(table["source"])
                    written.add(target)
                    atomic(target, Path(table["staged"]).read_bytes())
            return {"status": args.command + "-complete", "operations": receipt["operations"],
                    "note": "DataTable round-trip only; compile/PIE gameplay verification remains separate"}
    except BaseException:
        if before is not None:
            # Closed one-shot editor: restore on-disk assets, not a live editor's cache.
            affected = asset_paths if args.command == "push" else written
            restore(root, {n: b for n, b in before.items() if scoped(root, n) in affected})
        raise
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("pull", "push"))
    parser.add_argument("--engine", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    try:
        report, code = execute(args), 0
    except (SyncError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        report, code = {"status": "error", "error": str(exc)}, 3
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
