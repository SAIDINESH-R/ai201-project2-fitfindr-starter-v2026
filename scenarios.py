"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3: five different matching queries, one per try. Try 2
        # takes the price fallback, so the state check covers that path too.
        "name": "chosen item keeps its id",
        "query": "(five queries, one per try)",
        "queries": [
            "vintage graphic tee under $30",
            "pink shirt in 10$",
            "denim jacket under $50",
            "90s track jacket in size M",
            "silk slip dress under $40",
        ],
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 calls create_fit_card directly, exactly as written:
        # the same outfit for five listings covering all three platforms.
        "name": "fit card names the platform",
        "query": "(create_fit_card on five listings)",
        "kind": "fit_card",
        "outfit": "baggy jeans and white sneakers",
        "listing_ids": ["lst_006", "lst_003", "lst_010", "lst_004", "lst_011"],
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Criterion 5 as written: search_listings('vintage', max_price=B),
        # one budget per try. The before run reached it through "vintage under
        # $B" queries, which parsed to exactly this call; after the unit 4
        # improvement "under" means a $0–B ceiling, so the scenario now makes
        # the call the criterion names, directly.
        "name": "results inside the price window",
        "query": "(search_listings('vintage', max_price=B) at five budgets)",
        "kind": "search",
        "description": "vintage",
        "budgets": [22, 33, 38, 45, 51],
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Unit 4 second improvement: does the top search result have the item
        # word (the last word typed) in its title? One colour + item query per
        # category. Search only, no model calls. Diagnostic, not one of the
        # five criteria.
        "name": "top result is the item asked for",
        "query": "(five colour + item queries, one per try)",
        "kind": "top_result",
        "queries": ["black boots", "grey tee", "blue jeans", "black jacket", "brown belt"],
        "wardrobe": "example",
        "criterion": None,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    # Criteria 3 and 5 list one query per try under "queries"; criterion 4
    # uses "kind": "fit_card". run_eval.py::run_once handles both.
    #
    # Set "criterion" to the number in criteria.md that the scenario tests.
    # "criterion": None means a diagnostic run — useful to have, but it isn't
    # one of your five, and run_eval.py marks it as such in the table.
    #
    # For a state criterion, any normal query works — what you're checking is
    # what ends up in the session, not what the user typed.
    #
    # For a fit-card criterion, you probably want the SAME query listed more
    # than once, or several different items, depending on what your criterion
    # actually says.
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("kind") == "fit_card" and not scenario.get("listing_ids"):
            problems.append(f"scenario {i} is a fit_card scenario with no listing_ids")
        if scenario.get("kind") == "search" and not scenario.get("budgets"):
            problems.append(f"scenario {i} is a search scenario with no budgets")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
