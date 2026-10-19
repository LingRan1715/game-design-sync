"""Example data consumer, NOT an Unreal/gameplay test."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root / "GameData/skills.json").read_text(encoding="utf-8-sig"))
assert rows, "sample expects at least one skill"
assert len({row["Name"].casefold() for row in rows}) == len(rows)
for row in rows:
    assert isinstance(row["Enabled"], bool)
    assert 0 <= row["Damage"] <= 100000
    assert 0 <= row["Cooldown"] <= 600
print("Example data consumer passed; Unreal gameplay was not executed.")
