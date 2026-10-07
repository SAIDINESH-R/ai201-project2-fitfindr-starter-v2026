"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import math
import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def _words(text: str) -> set[str]:
    """Lowercase whole words. Splits on anything that isn't a letter or digit,
    so "Sweatshirt" is one word and never matches "shirt"."""
    return set(w for w in re.split(r"[^a-z0-9]+", text.lower()) if w)


def _size_pieces(size: str) -> set[str]:
    """Whole pieces of a size string, split on / spaces and brackets.
    "M/L" -> {"m", "l"}, "XL (oversized)" -> {"xl", "oversized"},
    "US 8.5" -> {"us", "8.5"}. Dots stay, so 8 never matches 8.5."""
    return set(p for p in re.split(r"[/\s()]+", size.lower()) if p)


def price_window(budget: float) -> tuple[float, float]:
    """The $10 window for a single budget: round up to the next multiple of 5,
    subtract 5 for the bottom, add 10 for the top. $33 -> (30, 40),
    $45 -> (40, 50), $5 -> (0, 10)."""
    bottom = math.ceil(budget / 5) * 5 - 5
    return float(bottom), float(bottom + 10)


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    limit: int | None = config.SEARCH_RESULT_LIMIT,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    query_words = _words(description)
    if not query_words:
        return []

    # Price: a custom range if both ends are given, the $10 window for a single
    # budget, nothing at all if there's no price.
    if min_price is not None and max_price is not None:
        low, high = min_price, max_price
    elif max_price is not None:
        low, high = price_window(max_price)
    else:
        low, high = None, None

    wanted_size = _size_pieces(size) if size else None

    scored = []
    for listing in load_listings():
        price = listing["price"]
        if low is not None and not (low <= price <= high):
            continue
        if wanted_size and not wanted_size <= _size_pieces(listing["size"]):
            continue

        title_words = _words(listing["title"])
        all_words = _words(" ".join([
            listing["title"],
            listing["description"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["category"],
        ]))
        title_hits = len(query_words & title_words)
        total_hits = len(query_words & all_words)
        if total_hits == 0:
            continue

        scored.append((title_hits, total_hits, price, listing))

    # Most title matches first, then most matches overall, then cheapest.
    scored.sort(key=lambda s: (-s[0], -s[1], s[2]))
    # limit=None returns every match (the loop uses it to look past the top 10).
    return [s[3] for s in scored[:limit]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _describe_item(item: dict) -> str:
    """One readable line about a listing, for a prompt."""
    return (
        f"{item['title']} ({item['category']}; colors: {', '.join(item['colors'])}; "
        f"style: {', '.join(item['style_tags'])}). {item['description']}"
    )


def _numbered_lines(text: str, count: int) -> list[str]:
    """Keep only lines that start with a number, renumbered 1..count."""
    lines = [
        re.sub(r"^\s*\d+[.)]\s*", "", line).strip()
        for line in text.splitlines()
        if re.match(r"^\s*\d+[.)]", line)
    ]
    return [f"{i}. {line}" for i, line in enumerate(lines[:count], start=1)]


def suggest_outfit(new_item: dict, wardrobe: dict, num_outfits: int = 2) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    num_outfits = max(1, min(5, int(num_outfits)))
    items = wardrobe.get("items") or []

    if items:
        owned = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])})"
            + (f" — {w['notes']}" if w.get("notes") else "")
            for w in items
        )
        prompt = (
            f"The user just found this thrifted item:\n{_describe_item(new_item)}\n\n"
            f"These are the only clothes they own:\n{owned}\n\n"
            f"Suggest exactly {num_outfits} different outfits built around the new "
            f"item. Use only pieces from the list above, named exactly as written. "
            f"Never invent a piece they don't own.\n"
            f"Reply with exactly {num_outfits} numbered lines (1. 2. ...), one "
            f"outfit per line, and nothing else."
        )
        note = ""
    else:
        prompt = (
            f"The user just found this thrifted item:\n{_describe_item(new_item)}\n\n"
            f"They haven't saved any clothes yet. Suggest exactly {num_outfits} "
            f"different outfits that pair it with everyday basics most people own "
            f"(e.g. plain jeans, white sneakers, a plain tee).\n"
            f"Reply with exactly {num_outfits} numbered lines (1. 2. ...), one "
            f"outfit per line, and nothing else."
        )
        note = "Your wardrobe is empty, so these use everyday basics:\n"

    lines = _numbered_lines(generate(prompt), num_outfits)
    if not lines:
        # The model ignored the format. Fall back to a plain suggestion rather
        # than returning "" — the spec says this tool never comes back empty.
        lines = [f"1. Wear the {new_item['title']} with simple basics in neutral colors."]
    return note + "\n".join(lines)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    price = f"${new_item['price']:.0f}"
    platform = new_item["platform"]

    if outfit and outfit.strip():
        # Brand only goes in when there is one, so "None" never reaches the model.
        brand = f"Brand: {new_item['brand']}\n" if new_item.get("brand") else ""
        prompt = (
            f"Item: {new_item['title']}\n{brand}Price: {price}\nPlatform: {platform}\n"
            f"Condition: {new_item['condition']}\n\n"
            f"How it's styled:\n{outfit}\n\n"
            f"Write a social media caption about this thrift find. 2 to 4 "
            f"sentences, then 1 to 3 hashtags on the last line. Include 2 or 3 emojis in the sentences. "
            f"Mention the item, the price ({price}) and the platform ({platform}) "
            f"once each. Sound like a real person posting, not a product listing, "
            f"and be specific about the vibe of the outfit. Reply with the caption "
            f"only."
        )
    else:
        # No outfit to talk about: describe the item on its own.
        prompt = (
            f"Item: {new_item['title']} (a {new_item['category']} piece)\n"
            f"Price: {price}\nPlatform: {platform}\n\n"
            f"Write a 2 to 4 sentence social media caption showing off this thrift "
            f"find, then 1 to 3 hashtags on the last line. Include 2 or 3 emojis in the sentences. "
            f"Mention the item, the price and the platform once each. Reply with "
            f"the caption only."
        )

    caption = generate(prompt).strip()
    if not caption:
        caption = f"Thrifted the {new_item['title']} for {price} on {platform} ✨ #thriftfind"
    return caption


# ── Tool 4 (stretch): check_owned ─────────────────────────────────────────────

def same_kind_and_colour(new_item: dict, wardrobe: dict) -> list[dict]:
    """Wardrobe items in the same category as new_item that share a colour.
    Owning a black jacket makes another black jacket a repeat."""
    category = new_item["category"].lower()
    colours = {c.lower() for c in new_item["colors"]}
    return [
        owned for owned in wardrobe.get("items") or []
        if owned["category"].lower() == category
        and colours & {c.lower() for c in owned["colors"]}
    ]



def check_owned(new_item: dict, wardrobe: dict) -> list[dict]:
    """
    Does the user already own something like this? Plain code, no model call.

    A wardrobe item counts as similar when it has the same category as the new
    item and shares at least one style tag (case-insensitive).

    Returns:
        The similar wardrobe item dicts, or an empty list when there are none.

    Test it from a terminal:
        python -c "from tools import check_owned; from utils.data_loader import get_example_wardrobe, load_listings; print(check_owned(load_listings()[6], get_example_wardrobe()))"
    """
    category = new_item["category"].lower()
    tags = {t.lower() for t in new_item["style_tags"]}
    return [
        owned for owned in wardrobe.get("items") or []
        if owned["category"].lower() == category
        and tags & {t.lower() for t in owned["style_tags"]}
    ]
