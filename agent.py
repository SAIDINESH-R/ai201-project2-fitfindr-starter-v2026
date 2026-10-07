"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import (
    search_listings, suggest_outfit, create_fit_card, check_owned, price_window, _words,
    same_kind_and_colour,
)
from generate import ModelUnavailable


# ── query parsing ─────────────────────────────────────────────────────────────

_NUMBER = r"(\d+(?:\.\d+)?)"

# Words that carry no meaning for the search. Without this, "a" and "for" would
# match almost every description and every query would look like a hit.
_FILLER = {
    "a", "an", "the", "i", "im", "me", "my", "want", "need", "looking", "for",
    "find", "show", "some", "something", "any", "in", "with", "and", "or", "of",
    "under", "below", "less", "than", "up", "to", "max", "between", "around",
    "size", "outfit", "outfits", "please", "cheap",
}


def parse_query(query: str) -> dict:
    """
    Pull description, size, min_price, max_price and num_outfits out of the
    query with regex. Whatever is left after removing those phrases (and filler
    words) is the description.
    """
    text = query.lower()
    parsed = {"description": "", "size": None, "min_price": None,
              "max_price": None, "num_outfits": 2}

    # Custom range first: "between $20 and $40", "$20-$40", "$20 to $40".
    match = (re.search(rf"between\s*\$?{_NUMBER}\s*(?:and|to|-)\s*\$?{_NUMBER}", text)
             or re.search(rf"\${_NUMBER}\s*(?:-|to)\s*\$?{_NUMBER}", text))
    if match:
        parsed["min_price"], parsed["max_price"] = float(match[1]), float(match[2])
        text = text.replace(match[0], " ")
    else:
        # A single budget: "$30", "30$", or "under 30".
        match = (re.search(rf"\${_NUMBER}", text)
                 or re.search(rf"{_NUMBER}\s*\$", text)
                 or re.search(rf"(?:under|below|less than|up to|max)\s+{_NUMBER}", text))
        if match:
            parsed["max_price"] = float(match[1])
            text = text.replace(match[0], " ")

    match = re.search(r"\b(\d+)\s*outfits?\b", text)
    if match:
        parsed["num_outfits"] = max(1, min(5, int(match[1])))
        text = text.replace(match[0], " ")

    match = re.search(
        r"\bsize\s+(us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?|one size|xxs|xs|xxl|xl|s|m|l|\d+(?:\.\d+)?)\b",
        text,
    )
    if match:
        parsed["size"] = match[1].upper()
        text = text.replace(match[0], " ")

    # Same whole-word split as the search, but kept in the user's order.
    words = [w for w in re.split(r"[^a-z0-9]+", text) if w and w not in _FILLER]
    parsed["description"] = " ".join(dict.fromkeys(words))
    return parsed


def _stop_message(parsed: dict) -> str:
    """Say what the user could change, based on the filters they used."""
    tips = []
    if parsed["size"]:
        tips.append(f"try without size {parsed['size']}")
    tips.append("try fewer or different words")
    words = parsed["description"] or "(no keywords)"
    return f"Nothing in the shop matches '{words}' at any price. " + ", or ".join(tips).capitalize() + "."


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "notice": None,              # set when the second branch (fallback) ran
        "alternatives": [],          # what the fallback showed instead
        "already_owned": [],         # similar wardrobe items, from check_owned
        "owned_match": None,         # top result repeats something owned; app asks the user
        "owned_like": [],            # the wardrobe items it repeats (same kind + colour)
        "passed_to": {},             # tool name -> id of the item it was handed
    }


def _something_new(session: dict, results: list[dict], repeats) -> list[dict]:
    """
    The user said "show me something new": the same kind of item as the top
    result (its category), minus anything that repeats what they own.

    If nothing like that fits their price, take the one priced closest to their
    budget and show the $10 window around it instead.
    """
    kind = results[0]["category"]
    fresh = [r for r in results if r["category"] == kind and not repeats(r)]
    p = session["parsed"]
    if fresh or p["max_price"] is None:
        return fresh[: config.SEARCH_RESULT_LIMIT]

    if p["min_price"] is not None:
        low, high = p["min_price"], p["max_price"]
    else:
        low, high = price_window(p["max_price"])

    everything = search_listings(p["description"], size=p["size"], limit=None)
    others = [r for r in everything if r["category"] == kind and not repeats(r)]
    if not others:
        return []

    def gap(r):
        if low <= r["price"] <= high:
            return 0
        return min(abs(r["price"] - low), abs(r["price"] - high))

    closest = min(others, key=gap)
    w_low, w_high = price_window(closest["price"])
    inside = [closest] + [
        r for r in others
        if r is not closest and w_low <= r["price"] <= w_high
    ]
    inside = inside[: config.SEARCH_RESULT_LIMIT]
    session["alternatives"] = inside
    session["notice"] = (
        f"No other colours between ${low:.0f} and ${high:.0f}. Showing {kind} "
        f"closest to your budget (${w_low:.0f}–${w_high:.0f}): "
        + ", ".join(f"{r['title']} (${r['price']:.0f})" for r in inside)
    )
    return inside


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(
    query: str,
    wardrobe: dict,
    bought_ids: set[str] | None = None,
    ask_if_owned: bool = False,
    skip_owned: bool = False,
) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass runs one step, writes its result into the session, and picks
    # the next step by reading the session back. The branch is in "search".
    next_step = "parse"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = parse_query(session["query"])
            next_step = "search"

        elif next_step == "search":
            p = session["parsed"]
            # "Something new" needs every match, not just the top 10, so it can
            # find the same kind of item in other colours.
            session["search_results"] = search_listings(
                p["description"], size=p["size"],
                max_price=p["max_price"], min_price=p["min_price"],
                limit=None if skip_owned else config.SEARCH_RESULT_LIMIT,
            )
            # THE BRANCH.
            if session["search_results"]:
                next_step = "select"
            elif p["max_price"] is not None:
                next_step = "fallback"
            else:
                session["error"] = _stop_message(p)
                next_step = "done"

        elif next_step == "fallback":
            # Second branch: nothing in the user's price range. Search again with
            # no price, keep title matches, and put the $10 window around the
            # cheapest of them.
            p = session["parsed"]
            query_words = set(p["description"].split())
            no_price = search_listings(
                p["description"], size=p["size"],
                limit=None if skip_owned else config.SEARCH_RESULT_LIMIT,
            )
            title_matches = [r for r in no_price if query_words & _words(r["title"])]
            if not title_matches:
                session["error"] = _stop_message(p)
                next_step = "done"
            else:
                cheapest = min(r["price"] for r in title_matches)
                low, high = price_window(cheapest)
                inside = sorted(
                    (r for r in title_matches if low <= r["price"] <= high),
                    key=lambda r: r["price"],
                )[: config.SEARCH_RESULT_LIMIT]
                session["search_results"] = inside
                session["alternatives"] = inside
                if p["min_price"] is not None:
                    asked_low, asked_high = p["min_price"], p["max_price"]
                else:
                    asked_low, asked_high = price_window(p["max_price"])
                session["notice"] = (
                    f"Nothing between ${asked_low:.0f} and ${asked_high:.0f}. Showing {len(inside)} outside your price "
                    f"range (${low:.0f}–${high:.0f}): "
                    + ", ".join(f"{r['title']} (${r['price']:.0f})" for r in inside)
                )
                next_step = "select"

        elif next_step == "select":
            # The first result. In the fallback the list is sorted by price, so
            # the first is also the cheapest.
            results = session["search_results"]
            bought = bought_ids or set()

            def repeats(item):
                return item["id"] in bought or same_kind_and_colour(item, session["wardrobe"])

            if skip_owned and results:
                results = _something_new(session, results, repeats)
            if not results:
                session["error"] = (
                    "Everything that matched is like something you already own. "
                    "Try different words or another colour."
                )
                next_step = "done"
            elif ask_if_owned and repeats(results[0]):
                # Style memory: the top result repeats something they own.
                # Stop and let the app ask whether to go ahead or look for
                # something new.
                session["owned_match"] = results[0]
                session["owned_like"] = same_kind_and_colour(results[0], session["wardrobe"])
                next_step = "done"
            else:
                session["selected_item"] = results[0]
                next_step = "check_owned"

        elif next_step == "check_owned":
            session["already_owned"] = check_owned(
                session["selected_item"],
                session["wardrobe"],
            )
            next_step = "outfit"

        elif next_step == "outfit":
            session["passed_to"]["suggest_outfit"] = session["selected_item"]["id"]
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"],
                session["wardrobe"],
                session["parsed"]["num_outfits"],
            )
            next_step = "fit_card"

        elif next_step == "fit_card":
            session["passed_to"]["create_fit_card"] = session["selected_item"]["id"]
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"],
                session["selected_item"],
            )
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
