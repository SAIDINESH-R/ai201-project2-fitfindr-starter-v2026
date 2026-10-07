# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr helps someone shop secondhand clothes. The user types a request like
`'vintage graphic tee under $30'`, and the agent searches 40 thrift listings for
the best match in a $10 price window around their budget, in their size. It returns the matched item (title,
price, size and platform), an outfit that pairs the item with clothes the user
already owns (or general styling tips if their wardrobe is empty), and a short
caption they could post about the find. If nothing matches, the agent stops
before the outfit step and tells the user what to change, such as changing the
budget or using different words.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches the 40 listings in `data/listings.json` for items
  whose title, description, style_tags, colors or category contain the words in
  `description`, keeping only those inside the price window and size.
- **Inputs:** `description` (str): keywords like `"vintage graphic tee"`.
  `size` (str or None): a size like `"L"`, or None to skip the size filter.
  `max_price` (float or None): the user's budget, or the top of their custom
  range, or None to skip the price filter.
  `min_price` (float or None, default None): the bottom of a custom range, or
  None when the user gave a single budget.
  - *Price rule:* if both `min_price` and `max_price` are given, keep listings
    priced from `min_price` to `max_price`, inclusive. If only `max_price` is
    given, it is a single budget and sets a $10 window, inclusive at both ends:
    round the budget up to the next multiple of 5 and subtract 5 for the
    bottom, and the top is bottom + 10. So $33 gives $30–40, $38 gives $35–45,
    $45 gives $40–50, and $5 gives $0–10. If neither is given, price is not
    filtered.
  - *Size rule:* the size is matched case-insensitively against whole pieces of
    the listing's size, split on `/`, spaces and brackets. `"L"` matches `L`,
    `M/L` and `L/XL`, but not `XL` or `W30 L30`.
  - *Keyword rule:* `description` and the listing's combined text are both
    lowercased and split into whole words on anything that isn't a letter or
    digit. Each query word that appears as a whole word in the listing counts
    as one match, so `"shirt"` matches "Flannel Shirt" but not "Sweatshirt".
    Listings with zero matches are dropped.
- **Returns:** A `list[dict]` of at most 10 listing dicts
  (`config.SEARCH_RESULT_LIMIT`). Each dict is the full listing: `id`, `title`,
  `description`, `category`, `style_tags`, `size`, `condition`, `price` (float),
  `colors`, `brand` (str or None) and `platform`. Results are ordered by the
  number of keywords found in the title (most first), then by total keyword
  matches, then by price (cheapest first).
- **When it has nothing:** Returns an empty list `[]`, never None and never an
  exception.

### `suggest_outfit`

- **What it does:** Asks the model to build outfits around the found item,
  using only pieces the user already owns.
- **Inputs:** `new_item` (dict): one listing dict from `search_listings`.
  `wardrobe` (dict): a dict with an `"items"` key holding a list of wardrobe
  item dicts (`name`, `category`, `colors`, `style_tags`, `notes`), which may be
  empty. `num_outfits` (int, default 2): how many outfits to suggest. The loop
  reads it from the query (e.g. `"3 outfits"`), and it is clamped to between 1
  and 5.
- **Returns:** A non-empty `str` holding a numbered list with exactly
  `num_outfits` lines (`1. ...`, `2. ...`). Each line is one outfit that names
  the new item plus pieces from the wardrobe by their `name`. It never names a
  piece the user doesn't own.
- **When it has nothing:** If `wardrobe["items"]` is empty, it returns a one-line
  note that the wardrobe is empty, followed by the same numbered list of
  `num_outfits` lines. These outfits pair the item with everyday basics (e.g.
  plain jeans, white sneakers) instead of owned pieces. It never returns `""` and never raises.

### `create_fit_card`

- **What it does:** Asks the model to write a short social media caption about
  the thrifted find and how it's styled.
- **Inputs:** `outfit` (str): the outfit text from `suggest_outfit`.
  `new_item` (dict): the same listing dict that went into `suggest_outfit`.
- **Returns:** A non-empty `str`: a caption of 2–4 sentences, followed by 1–3
  hashtags, with a few emojis. It names the item, its price and its platform
  once each, and mentions the brand only when `brand` is not None (so "None"
  never appears in the caption).
- **When it has nothing:** If `outfit` is empty or only whitespace, it still
  calls the model, giving it only the item's category, title and price, and
  returns a 2–4 sentence caption describing the item on its own. It never
  returns `""` and never raises.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns results, take the first one as
the selected item and go to `suggest_outfit`. If it returns an empty list and
the query had a price, search again with no price filter (second branch, see
Stretch Features). If that finds no title match, or the query had no price, put a
message in `session["error"]` that names what to change, based on the filters
that were used (e.g. "try without size M", "try fewer or different words"), and
stop without calling `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex. `under $30` becomes `max_price = 30.0`.
`between $20 and $40` or `$20-$40` becomes `min_price = 20.0` and
`max_price = 40.0`. `size M` becomes `size = "M"`, and `3 outfits` becomes `num_outfits = 3`. The
words left over after removing those phrases become `description`.

**What moves through the session:** `query` → `parsed` (description, size,
min_price, max_price, num_outfits) → `search_results` → `selected_item` (the first
result) → `outfit_suggestion` → `fit_card`. If the search is empty, `error` is
set and the later fields stay None.

---

## Stretch Features (planned)

<!-- Declared before building, as the rubric requires. Each one gets a run log
     here once it's built. -->

### Second branch: over-budget alternatives

- **Condition:** the search with the user's price returns nothing, but the same
  search with no price filter returns at least one listing with a query word in
  its title. Example: `'pink shirt under $10'` (the $10 window is $5–15 and no
  shirt is priced there).
- **What the loop does instead:** keeps only the no-price results that have a
  query word in their title (so `"shirt"` returns shirts, not a pink tee that
  only matched `"pink"`). It takes the cheapest of those and runs the same
  price window rule on its price: cheapest $37 gives $35–45, cheapest $20 gives
  $15–25. It shows the title matches inside that window, cheapest first and up
  to 10, labeled as outside your price range (they can be cheaper or pricier
  than the budget), then selects the cheapest one and continues to
  `suggest_outfit` and `create_fit_card` with it.
- **How it differs from the empty-search stop:** the stop only happens when no
  listing has a query word in its title at any price.
- **Cases the normal search already covers:** `'pink shirt under $30'` with no
  pink shirt in the window still returns the other shirts in the window,
  because every query word counts on its own. `'shirt'` with no price returns
  the best matches first.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

Budget $30 gives the $25–35 window, so both results are inside it. The cargo
pants match only because their description mentions "a long tee".

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
1. Vintage Levi's 501 Jeans — Medium Wash + White ribbed tank top + Black cropped zip hoodie + Chunky white sneakers + Black crossbody bag
2. Vintage Levi's 501 Jeans — Medium Wash + Oversized grey crewneck sweatshirt + Black combat boots + Brown leather belt
```

Two outfits (the default), and every piece is from the example wardrobe.

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans for just $38 and I am never taking them off 👖✨ Throwing them on with crisp white sneakers gives the ultimate effortless, off-duty coffee run vibe. Snagged them over on depop before anyone else could! 🏃💨

#ThriftFind #VintageLevis #DepopFinds

$ AI201_CACHE=0 python -c "...same command..."
Nothing beats the effortless vibe of broken-in denim paired with crisp white kicks for a sunny weekend coffee run. Snagged these classic vintage Levi's 501 jeans for just $38 and I'm honestly obsessed with how well they fit 👖✨. Finding timeless pieces like this on depop is literally my favorite hobby.

#ThriftFind #VintageDenim #DepopStyle

$ AI201_CACHE=0 python -c "...same command..."
Scored these classic medium wash Levi's 501s on Depop for just $38, and they honestly fit like a dream. 👖✨ Threw them on with some beat-up white sneakers for that effortless, 90s-off-duty-model casual look. Grab them before I change my mind and keep them forever! 🤍

#vintagelevis #depopfinds #9sstyle
```

Run without `AI201_CACHE=0`, the same command printed the same caption word for
word five times: the cache handed back the saved answer. With the cache off,
every caption is different and each one names $38 and Depop.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
