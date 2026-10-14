"""
Your MCP server. ← UNIT 4, MILESTONE 1

Right now your tools only exist inside your own program. Nothing else can reach
them. MCP is an agreed shape you wrap a tool in so that anything speaking the
same protocol can call it — your agent today, a different agent tomorrow,
someone else's app after that.

**You're moving one tool. Not three.** The point is to see the seam.
`search_listings` is the one to move: it doesn't call the model, so nothing is
slow and nothing changes between runs while you're learning the shape.

    python mcp_server.py        starts the server (it will just sit there — that's right)
    python mcp_client.py        asks the server what it offers

─────────────────────────────────────────────────────────────────────────────
TODO — register one tool.

Uncomment the block below and fill it in. Three things matter:

  1. **The name.** Exactly what your agent will ask for.

  2. **The description.** This is the part that isn't code and matters most.
     Write it before you look at the example. You are not writing it for your
     agent — you're writing it for an agent someone else builds, that will
     never see your implementation. That isn't hypothetical; it's what every
     MCP server on the registry is.

     Two things to get right: name units and types ("price" is ambiguous,
     "max_price, in whole dollars" isn't), and state the empty case. Last unit
     the empty case was on your spec sheet for your loop's benefit. Here it's
     part of a published contract.

  3. **The typed inputs.** These come straight from your Tool Inventory. If the
     types here don't match your README, one of the two is wrong — fix it.

Then point your agent at it. In `run_agent()`, swap the direct call:

    results = search_listings(description, size, max_price)

for the MCP one:

    from mcp_client import call_tool
    results = call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })

**What comes back should not change.** If it does, that difference is your
first clue about what your tool was really returning before.

🛑 Stop rule: if this isn't connecting after 40 minutes, stop. Keep your direct
call, and write down in your README exactly where it broke — the error text and
the last thing that worked. Then carry on to Milestone 2. Everything after this
works with a direct call, and **a documented failure earns the point in full.**
─────────────────────────────────────────────────────────────────────────────
"""

from mcp.server.fastmcp import FastMCP

from tools import search_listings as _search_listings_impl  # noqa: F401 — you'll use this below
from tools import check_owned as _check_owned_impl

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


# ── search_listings, served over MCP ──────────────────────────────────────────

@mcp.tool()
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    limit: int | None = 10,
) -> list[dict]:
    """
    Search 40 secondhand clothing listings by keywords and return the best matches.

    Pass the item words as `description` (e.g. "graphic tee"), not a full
    sentence. `size` (e.g. "M") is optional. `max_price` is the budget in US
    dollars, but it is NOT a ceiling: it sets a $10 window around the budget
    (30 → $25–35). To search an exact range instead, pass both `min_price` and
    `max_price`. `limit` caps how many results come back (default 10, null for
    all).

    Returns a list of listing objects (id, title, description, category,
    style_tags, size, condition, price, colors, brand, platform), best match
    first. Returns an empty list [] when nothing matches, never an error.
    """
    return _search_listings_impl(
        description, size=size, max_price=max_price, min_price=min_price, limit=limit,
    )


# ── check_owned, served over MCP (unit 4 stretch: a second tool) ─────────────

@mcp.tool()
def check_owned(new_item: dict, wardrobe: dict) -> list[dict]:
    """
    Check whether someone already owns clothes similar to an item they're
    considering, so they don't buy a near-duplicate.

    `new_item` is one listing object as returned by search_listings (it needs
    `category` and `style_tags`). `wardrobe` is an object with an "items" list;
    each item needs `category` and `style_tags` (and usually `name`). The list
    may be empty.

    Returns the wardrobe items that are similar: same category as new_item and
    at least one shared style tag (case-insensitive). Returns an empty list []
    when nothing is similar or the wardrobe is empty, never an error.
    """
    return _check_owned_impl(new_item, wardrobe)

# ──────────────────────────────────────────────────────────────────────────────
#
# Two notes on the block above.
#
# The registered name is the *function* name — so the block above registers
# "search_listings", which is exactly what call_tool("search_listings", ...)
# asks for. That is also why the import at the top of this file brings the real
# implementation in under an alias: without it, the registered function and the
# one it calls would be the same name, and the tool would call itself.
#
# FastMCP builds the input schema from your type hints, which is why the hints
# are not optional here. `description: str` becomes a required string;
# `max_price: float | None = None` becomes an optional number. Getting these
# wrong is the most common reason a call is rejected.


if __name__ == "__main__":
    mcp.run()
