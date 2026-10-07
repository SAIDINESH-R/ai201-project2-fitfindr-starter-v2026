"""
Style memory: the wardrobe the agent remembers between runs.

A bought item is a pending purchase until its return window closes. Then it
becomes a wardrobe item, and every later run can style with it.

Everything lives in data/my_wardrobe.json:

    {
      "items":   [ ...wardrobe items, same shape as the example wardrobe... ],
      "pending": [ {"listing_id": "lst_007", "bought_on": "2026-10-06", "item": {...}} ]
    }

The file doesn't exist until the first purchase. Until then the example
wardrobe is used, exactly as before.
"""

import json
import os
from datetime import date, timedelta

from utils.data_loader import get_example_wardrobe

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "my_wardrobe.json")

# How long a purchase can still be returned. Only after this does it count as
# owned.
RETURN_WINDOW_DAYS = 14


def _read() -> dict | None:
    if not os.path.exists(MEMORY_PATH):
        return None
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(memory: dict) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _to_wardrobe_item(listing: dict) -> dict:
    """A listing, reshaped into a wardrobe item."""
    return {
        "id": f"w_{listing['id']}",
        "name": listing["title"],
        "category": listing["category"],
        "colors": listing["colors"],
        "style_tags": listing["style_tags"],
        "notes": f"Thrifted on {listing['platform']} for ${listing['price']:.0f}",
    }


def load_wardrobe(today: date | None = None) -> dict:
    """
    The wardrobe for this run. Moves any pending purchase whose return window
    has closed into the items first. Falls back to the example wardrobe when
    nothing has been bought yet.
    """
    memory = _read()
    if memory is None:
        return get_example_wardrobe()

    today = today or date.today()
    cutoff = today - timedelta(days=RETURN_WINDOW_DAYS)
    still_pending = []
    for purchase in memory["pending"]:
        if date.fromisoformat(purchase["bought_on"]) <= cutoff:
            memory["items"].append(purchase["item"])
        else:
            still_pending.append(purchase)

    if len(still_pending) != len(memory["pending"]):
        memory["pending"] = still_pending
        _write(memory)

    return {"items": memory["items"]}


def bought_ids() -> set[str]:
    """Listing ids the user has bought, pending or kept."""
    memory = _read()
    if memory is None:
        return set()
    kept = {w["id"][2:] for w in memory["items"] if w["id"].startswith("w_lst_")}
    pending = {p["listing_id"] for p in memory["pending"]}
    return kept | pending


def record_purchase(listing: dict, today: date | None = None) -> str:
    """Save a bought listing as pending. Returns a line to show the user."""
    memory = _read() or {"items": get_example_wardrobe()["items"], "pending": []}

    owned_ids = {w["id"] for w in memory["items"]}
    pending_ids = {p["listing_id"] for p in memory["pending"]}
    if f"w_{listing['id']}" in owned_ids or listing["id"] in pending_ids:
        return f"You already bought {listing['title']}."

    bought_on = today or date.today()
    memory["pending"].append({
        "listing_id": listing["id"],
        "bought_on": bought_on.isoformat(),
        "item": _to_wardrobe_item(listing),
    })
    _write(memory)
    closes = bought_on + timedelta(days=RETURN_WINDOW_DAYS)
    return (
        f"Bought {listing['title']} ({listing['id']}). It joins your wardrobe "
        f"when the return window closes on {closes.isoformat()}, or now with: "
        f"python app.py keep {listing['id']}"
    )


def keep(listing_id: str) -> str:
    """Close the return window early: move a pending purchase into the items."""
    memory = _read()
    if memory is None:
        return "Nothing has been bought yet."

    for purchase in memory["pending"]:
        if purchase["listing_id"] == listing_id:
            memory["pending"].remove(purchase)
            memory["items"].append(purchase["item"])
            _write(memory)
            return f"Kept {purchase['item']['name']}. It's in your wardrobe now."

    return f"No pending purchase with id {listing_id}."
