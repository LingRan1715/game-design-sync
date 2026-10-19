"""Runs INSIDE Unreal Editor Python. Invoked by ue_bridge.py, never by host Python."""
import json
import math
import os
from pathlib import Path
import traceback


def comparable(rows):
    if not isinstance(rows, list):
        raise ValueError("DataTable JSON must be an array")
    result = {}
    for row in rows:
        name = row.get("Name")
        if not isinstance(name, str) or not name or name.casefold() in result:
            raise ValueError("Expected unique case-insensitive Name keys")
        result[name.casefold()] = row
    return result


def equal(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-6)
    return type(left) is type(right) and left == right


def execute(request, unreal):
    operations = []
    for entry in request["tables"]:
        asset = unreal.EditorAssetLibrary.load_asset(entry["asset"])
        if not isinstance(asset, unreal.DataTable):
            raise ValueError(f"Not an existing DataTable: {entry['asset']}")
        output = entry["staged"]
        if request["mode"] == "push":
            with open(entry["source"], encoding="utf-8-sig") as stream:
                expected = comparable(json.load(stream))
            struct = unreal.DataTableFunctionLibrary.get_data_table_row_struct(asset)
            if not struct:
                raise ValueError("DataTable has no row struct")
            if not unreal.DataTableFunctionLibrary.fill_data_table_from_json_file(asset, entry["source"], struct):
                raise ValueError("DataTable import failed")
        if not unreal.DataTableFunctionLibrary.export_data_table_to_json_file(asset, output):
            raise ValueError("DataTable export failed")
        with open(output, encoding="utf-8-sig") as stream:
            actual = comparable(json.load(stream))
        if request["mode"] == "push":
            if not equal(expected, actual):
                raise ValueError("DataTable round-trip mismatch; refusing to save asset")
            if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
                raise ValueError("DataTable save failed")
        operations.append({"asset": entry["asset"], "rows": len(actual)})
    return operations


def main():
    import unreal
    request_path = Path(os.environ["GDS_UE_REQUEST"])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result = {"token": request["token"], "success": False}
    try:
        result["operations"] = execute(request, unreal)
        result["success"] = True
    except Exception:
        result["error"] = traceback.format_exc()
        unreal.log_error(result["error"])
    finally:
        Path(str(request_path) + ".result.json").write_text(json.dumps(result), encoding="utf-8")
    if not result["success"]:
        raise RuntimeError("Game design sync bridge failed; inspect result and editor logs")


if __name__ == "__main__":
    main()
