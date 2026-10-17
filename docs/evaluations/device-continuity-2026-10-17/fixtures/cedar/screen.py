import json
from pathlib import Path
import theme

def button(amount):
    strings=json.loads(Path(__file__).with_name("strings.json").read_text())
    return {"enabled": amount > 0, "color": theme.COLORS["enabled" if amount > 0 else "disabled"], "label": strings["confirm"]}
