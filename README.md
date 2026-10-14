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
> That last command runs the full agent: search, outfit and fit card.

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
the best match within their budget ("under $30" means up to $30; a bare "$30"
means a $10 window around it), in their size. It
returns the matched item (title, price, size and platform), an outfit that
pairs the item with clothes the user already owns (or general styling tips if
their wardrobe is empty), and a short caption they could post about the find.
If the item exists but nothing fits the price, it shows the closest-priced
alternatives and styles the cheapest. If nothing in the shop matches the words
at all, it stops before the outfit step and tells the user what to change, such
as using different words or dropping the size.


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
  `limit` (int or None, default 10): the most results to return, or None for
  every match. The loop passes None only when looking for "something new" in
  other colours, so it can look past the top 10.
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
- **Returns:** A `list[dict]` of at most `limit` listing dicts (10 by default,
  `config.SEARCH_RESULT_LIMIT`). Each dict is the full listing: `id`, `title`,
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
stop without calling `suggest_outfit`. One more stop, from style memory, when
the app passes `ask_if_owned=True`: if the top result is a listing the user
already bought, or the same category in a colour they already own, stop with
`session["owned_match"]` set so the app can ask whether to show it anyway or
look for the same kind in other colours.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex. `under $30` (or below, less than, up to,
max) is a ceiling and becomes `min_price = 0.0`, `max_price = 30.0`, changed
in unit 4 (see The Improvement). A bare budget, `$30` or `in 30$`, becomes
`max_price = 30.0`, which `search_listings` turns into the $10 window.
`between $20 and $40` or `$20-$40` becomes `min_price = 20.0` and
`max_price = 40.0`. `size M` becomes `size = "M"`, and `3 outfits` becomes `num_outfits = 3`. The
words left over after removing those phrases become `description`.

**What moves through the session:** `query` → `parsed` (description, size,
min_price, max_price, num_outfits) → `search_results` → `selected_item` (the first
result) → `already_owned` (from `check_owned`) → `outfit_suggestion` →
`fit_card`. Before each model tool is called, the loop records the id of the
item it hands over in `passed_to`, so criterion 3 can compare it with
`selected_item`. If the search is empty, `error` is set and the later fields stay
None. The fallback branch also sets `notice` and `alternatives`, and the
style-memory stop sets `owned_match` and `owned_like` instead of
`selected_item`.

---

## Stretch Features

<!-- Declared before building, as the rubric requires (see the commit
     history). Each one has a run log below now that it's built. -->

### Second branch: alternatives outside the price range

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
- **Run log (branch taken):**

  ```
  $ python app.py ask 'pink shirt in 10$'

    Nothing between $5 and $15. Showing 2 outside your price range ($15–$25): Vintage Polo Shirt — Forest Green ($18), Oversized Flannel Shirt — Plaid Red/Black ($22)

    Found:    Vintage Polo Shirt — Forest Green — $18.0 on thredUp

    Outfit:   1. Vintage Polo Shirt — Forest Green + Baggy straight-leg jeans, dark wash + Chunky white sneakers + Brown leather belt
  2. Vintage Polo Shirt — Forest Green + Wide-leg khaki trousers + Black combat boots + Brown leather belt

    Fit card: Scored this forest green Ralph Lauren polo on thredUp for just $18, and it’s giving major retro campus energy. I love dressing it down with baggy dark wash jeans and chunky sneakers, or leaning into the smart-casual look with khaki trousers and combat boots 🌲✨👞

  #ThriftFind #VintageStyle #Menswear
  ```

  The $10 budget gives a $5–15 window with no shirts in it, so the loop took the
  fallback instead of stopping. The cheapest shirt is $18, which sets a $15–25
  window, and the loop styled the cheapest shirt in it.
- **Where it lives:** `agent.py::run_agent`, the `"fallback"` step.

### Fourth tool: `check_owned`

- **What it does:** Checks whether the user already owns something like the
  selected item, so they don't buy a near-duplicate. Plain code, no model call.
- **Inputs:** `new_item` (dict): the selected listing. `wardrobe` (dict): the
  wardrobe with its `"items"` list.
- **Returns:** A `list[dict]` of the wardrobe items that are "similar": same
  `category` as the new item and at least one shared `style_tags` entry
  (compared case-insensitively). The agent shows them as a heads-up, e.g.
  "You already own something similar: Vintage black denim jacket".
- **When it has nothing:** Returns an empty list `[]`, and the agent shows no
  heads-up.
- **When it runs:** on every run that selects an item, right after `select`
  and before `suggest_outfit`. The result goes into `session["already_owned"]`.
- **Run log (the agent calling it):** the "Heads-up" line is `check_owned`'s
  result. The example wardrobe has a "Vintage black denim jacket" (outerwear,
  tags denim/vintage/classic), which matches the found jacket's category and
  shares tags.

  ```
  $ python app.py ask 'denim jacket under $45' --buy

    Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

    Heads-up: you already own something similar: Vintage black denim jacket
  ```
- **Where it lives:** `tools.py::check_owned`, called from the `"check_owned"`
  step in `agent.py::run_agent`.

### Style memory: buy, return window, wardrobe

- **What it does:** The agent remembers what the user bought between runs. A
  bought item only joins the wardrobe once its return window has closed.
- **How it works:**
  1. `python app.py ask '...' --buy` records the selected item as a pending
     purchase with today's date.
  2. The return window is 14 days. At the start of every run, pending items
     bought 14 or more days ago move into the wardrobe.
  3. `python app.py keep <listing id>` closes the window early ("I'm keeping
     it") and moves that item into the wardrobe straight away.
  4. A listing moved into the wardrobe becomes a wardrobe item: its title as
     `name`, plus its `category`, `colors` and `style_tags`.
- **Where it's stored:** `data/my_wardrobe.json`, created from the example
  wardrobe on the first purchase, with `"items"` and `"pending"` lists. Every
  later run loads it instead of the example wardrobe. It is committed so the
  memory is visible in the repo.
- **How a later run is shaped by an earlier one:** after buying and keeping the
  Denim Jacket, `suggest_outfit` can use it in outfits, and `check_owned` warns
  when the search finds another jacket.
- **Added after building: "you already own this kind".** Finding the exact
  item you bought, or another black jacket when you already own one, isn't
  much help. When `app.py` runs the agent it passes `ask_if_owned=True`. If the
  top result is a listing the user bought (pending or kept), or is the same
  category as a wardrobe item and shares a colour with it
  (`tools.py::same_kind_and_colour`), `run_agent` stops before
  `suggest_outfit` and sets `session["owned_match"]`. `app.py` then asks "Show
  this one anyway (b) or <category> in other colours (n)?".
  - `b` runs again normally and styles that item.
  - `n` runs again with `skip_owned=True`: it searches every match (not just
    the top 10), keeps only the same category as the item it asked about, and
    drops bought listings and colours the user already owns in that category.
    The price window still applies, and with no price it takes the best match.
    If nothing of that kind in another colour fits the window, it searches
    again with no price, picks the matching item priced closest to the
    budget, and shows the $10 window around that one
    (`agent.py::_something_new`). For example, `'black jacket under $75'` has
    only the black Leather Bomber in $70–80, so `n` gives "No other colours
    between $70 and $80. Showing outerwear closest to your budget ($40–$50):
    90s Track Jacket — Navy/White Stripe ($45)".
  - With no keyboard to ask, it picks `n`. `run_eval.py` calls
    `run_agent(query, wardrobe)` without `ask_if_owned`, so evaluation runs
    never stop to ask.
- **Run log: two runs, the second shaped by the first.**

  Run 1 buys the jacket (the heads-up lists one similar item):

  ```
  $ python app.py ask 'denim jacket under $45' --buy

    Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

    Heads-up: you already own something similar: Vintage black denim jacket
    ...
    Bought Denim Jacket — Light Wash, Cropped (lst_007). It joins your wardrobe when the return window closes on 2026-10-20, or now with: python app.py keep lst_007

  $ python app.py keep lst_007

    Kept Denim Jacket — Light Wash, Cropped. It's in your wardrobe now.
  ```

  Run 2 is a later search. It recognises that the user already owns a black
  jacket, asks, and on `n` finds outerwear in another colour. The heads-up now
  lists the jacket bought in run 1, because it's in the remembered wardrobe:

  ```
  $ python app.py ask 'black jacket'

    Found 90s Leather Bomber — Black ($75, lst_022).
    You already own the same kind in this colour: Vintage black denim jacket
    Show this one anyway (b) or outerwear in other colours (n)? [n] n

    Found:    90s Track Jacket — Navy/White Stripe — $45.0 on poshmark

    Heads-up: you already own something similar: Vintage black denim jacket, Denim Jacket — Light Wash, Cropped

    Outfit:   1. 90s Track Jacket — Navy/White Stripe + White ribbed tank top + Baggy straight-leg jeans, dark wash + Chunky white sneakers
  2. 90s Track Jacket — Navy/White Stripe + White ribbed tank top + Wide-leg khaki trousers + Black combat boots + Black crossbody bag

    Fit card: Just scored the ultimate vintage Champion track jacket on Poshmark for only $45 🧥✨ It gives off the best effortless 90s athletic vibe, whether I'm styling it super casually with baggy denim or mixing it up with khaki trousers and combat boots.

  #ThriftFind #VintageStreetwear #PoshmarkStyle
  ```

  The remembered wardrobe is in `data/my_wardrobe.json`.
- **Known limitation:** the track jacket counts as "similar" to the denim
  jackets only because all three are tagged "vintage", which most listings
  are. Matching on a rarer tag would make the heads-up more useful.
- **Known limitation:** "same kind" comes from the top result's category, and
  the keyword search treats a colour word like an item word. With
  `'black jacket under $20'` no jacket fits $15–25, so the top result is a
  black top that only matched "black", and the question asks about tops.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found Vintage Graphic Hoodie — Faded Black ($26, lst_015).
  You already own the same kind in this colour: Oversized grey crewneck sweatshirt, Black cropped zip hoodie
  Show this one anyway (b) or tops in other colours (n)? [n] b

  Found:    Vintage Graphic Hoodie — Faded Black — $26.0 on depop

  Heads-up: you already own something similar: Black cropped zip hoodie

  Outfit:   1. Vintage Graphic Hoodie — Faded Black + Baggy straight-leg jeans, dark wash + Black combat boots + Black crossbody bag
2. Vintage Graphic Hoodie — Faded Black + Wide-leg khaki trousers + Chunky white sneakers + Brown leather belt

  Fit card: Scored this perfectly faded graphic hoodie on depop for just $26, and I'm obsessed with the worn-in grunge look. 🖤 Throw it on with baggy dark denim and combat boots for an effortless 90s vibe, or dress it up with khaki trousers for that cool thrifted contrast. ✨ It's seriously the ultimate cozy staple for everyday styling.

#thriftfinds #depop #streetwear

2 model calls this session, 570 prompt + 141 output tokens
```

The $30 budget sets a $25–35 window. The only graphic tees cost $18 and $24, so
they fall below it, and the hoodie wins on "vintage" and "graphic" in its
title. The hoodie is black and charcoal, and the wardrobe already has tops in
both colours, so the style-memory question came first. Answering `b` styles it
anyway.

**A query that matches nothing**

```
$ python app.py ask 'tuxedo'

  Nothing in the shop matches 'tuxedo' at any price. Try fewer or different words.

0 model calls this session
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

**How I worked overall:** I made every design decision myself (the price
window, the size and keyword rules, the outfit count, what the fit card must
contain, and each criterion's check, target and reason) by answering Claude's
questions, often multiple-choice. Claude turned my choices into the spec and
criteria wording, wrote the code from my spec, and explained each part before
I ran every test command myself. The moments below are where that back and
forth changed the design.

**Moment 1: the size trap**

- *What I asked for:* I asked Claude to explain the size warning in
  `tools.py`, because I thought `L` matching `XL` was a lowercase problem.
- *What came back:* It wasn't about case. Python's `in` matches part of a
  word, so `"l" in "xl (oversized)"` and `"l" in "w30 l30"` are both True, and a
  search for size L would return an XL flannel and a pair of jeans.
- *What I changed:* I wrote a whole-piece size rule into my Tool Inventory
  before writing any code: split the size on `/`, spaces and brackets and
  compare whole pieces, so `L` matches `L`, `M/L` and `L/XL` but not `XL` or
  `W30 L30`. `search_listings` follows that rule, and size L now returns only
  `L` and `M/L`.

**Moment 2: shirt vs sweatshirt**

- *What I asked for:* I asked Claude whether my search design made sense.
- *What came back:* It pointed out that the same substring problem hits
  keywords too: the data has an "Oversized Crewneck Sweatshirt", and
  `"shirt" in "sweatshirt"` is True, so a search for "shirt" would return
  sweatshirts.
- *What I changed:* I changed the keyword rule in my spec to whole words
  (split on anything that isn't a letter or digit). Now `'shirt'` returns the
  Polo Shirt and Flannel Shirt but no Sweatshirt. The cost is that plurals
  don't match ("tees" won't find "tee"), which I noted in criterion 1.

**Moment 3: a vague prompt**

- *What I asked for:* My first `create_fit_card` prompt asked the model to
  "use a few emojis", as my spec promised.
- *What came back:* Three captions in a row with no emojis at all.
- *What I changed:* I made the instruction specific, "Include 2 or 3 emojis in
  the sentences", and the next captions had them (🎸 👟✨).

**Moment 4: identical fit cards**

- *What I asked for:* I ran the same `create_fit_card` command five times, as
  the milestone asked, and asked Claude why all five captions were word for
  word the same.
- *What came back:* It wasn't the temperature (0.9 in `config.py`). It was
  `CACHE_ENABLED`: after the first call, the adapter handed back the saved
  answer for the identical prompt.
- *What I changed:* I re-ran with `AI201_CACHE=0` and got a different caption
  every time, each still naming $38 and Depop. I left the cache on for
  building, since it saves quota, and I use `AI201_CACHE=0` when I need real
  variation.

**Moment 5: the model copied the prompt's details**

- *What I asked for:* `suggest_outfit` lists the wardrobe in the prompt as
  "name (category; colors: ...)" and asked for pieces "named exactly as
  written".
- *What came back:* Once the wardrobe changed, the outfits started repeating
  the brackets: "Baggy straight-leg jeans, dark wash (bottoms; colors: dark
  blue, indigo), Black combat boots (shoes; colors: black)…". The earlier
  clean output had been luck.
- *What I changed:* I told the model to write only the piece names joined with
  " + ", starting with the new item, and to leave out the details in brackets.
  The next outfits came back as "Vintage Graphic Hoodie — Faded Black + Baggy
  straight-leg jeans, dark wash + Black combat boots + Black crossbody bag".

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Unit 4 Stretch Features (planned)

<!-- Declared before building, as the rubric requires. Each gets its evidence
     here once built. -->

### A second tool on MCP: `check_owned`

`search_listings` moves onto MCP first (the required tool). `check_owned` will
be registered on the same server, with the same inputs and return value as in
the Unit 3 Stretch Features, and `run_agent` will call it through
`mcp_client.call_tool`. Evidence: a loop trace with both MCP calls visible.

### Retry with looser constraints: drop the size

If `search_listings` returns an empty list and the query had a size, the loop
retries the search once with `size=None`, records which constraint was dropped
(in the session and the trace, e.g. "retry: dropped size M"), and continues
with those results. If the retry is also empty, the existing price fallback
and stop rules apply as before. Evidence: a run log showing the retry and the
dropped constraint.

### A second measured improvement

After the first improvement, a second change chosen from the diagnosis, run
with `python run_eval.py` and logged as a third run log in the same table
format, with a statement of whether it helped.

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

Run with `python run_eval.py --label before` (5 tries per scenario, caching
off, 45 model calls). Full log: `results/run_2026-10-14_0246_before.md`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1. (revised in unit 4) …and the selected item is a tee | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The chosen item keeps its id through every tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card names where to buy the item | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search results stay inside the budget's price window | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

What each try ran, and how PASS was decided:

1. `'vintage graphic tee under $30'` five times. PASS = not stopped early and
   `fit_card` is set.
2. `'designer ballgown size XXS under $5'` five times. PASS = stopped before
   `suggest_outfit` (`fit_card` is None) with a message naming what to change.
3. One query per try: `'vintage graphic tee under $30'`, `'pink shirt in 10$'`
   (takes the price fallback), `'denim jacket under $50'`,
   `'90s track jacket in size M'`, `'silk slip dress under $40'`. PASS =
   `selected_item` id, `search_results[0]` id and both `passed_to` ids are
   the same.
4. `create_fit_card('baggy jeans and white sneakers', item)` for `lst_006`
   (depop), `lst_003` and `lst_010` (thredUp), `lst_004` and `lst_011`
   (poshmark). PASS = the caption names that listing's platform (case
   ignored).
5. `'vintage under $B'` for B = 22, 33, 38, 45, 51, which parses to
   `search_listings('vintage', max_price=B)`. PASS = at least one result and
   every price inside the window ($20–30, $30–40, $35–45, $40–50, $50–60).

`run_eval.py` runs `agent.py::run_agent` for every scenario except criterion
4, which calls `tools.py::create_fit_card` directly (`run_eval.py::run_once`
was extended so a scenario can list one input per try).

**Real output from one try per criterion**, from
`results/run_2026-10-14_0246_before.md`, produced by `run_eval.py::main`
running `agent.py::run_agent`:

Criterion 1, try 1 (`agent.py::run_agent`):

```
- stopped early: no
- selected_item: Vintage Graphic Hoodie — Faded Black ($26.0, depop)
- search_results: 9

Fit card:
Scored this perfectly broken-in faded black graphic hoodie for just $26 on depop 🖤. The wash gives it that ultimate grunge look whether you're throwing it on with baggy denim or dressing it up with structured khaki trousers. It’s giving effortless 90s streetwear without even trying 🛹✨.

#thrifted #streetwear #depopfinds
```

Criterion 2, try 1 (`agent.py::run_agent`, the fallback then the stop):

```
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, but the query had a price → fallback
[3] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', price='none (fallback)'
      out: [] (empty)
      →    fallback: no title match at any price → stop
- stopped early: yes — Nothing in the shop matches 'designer ballgown' at any price. Try without size xxs, or try fewer or different words.
```

Criterion 3, try 2 (`agent.py::run_agent`, through the fallback):

```
- Input: `pink shirt in 10$`
- selected_item id: lst_024, platform: thredUp
- search_results[0] id: lst_024
- passed_to: {'suggest_outfit': 'lst_024', 'create_fit_card': 'lst_024'}
```

Criterion 4, try 4 (`tools.py::create_fit_card`, platform poshmark):

```
Scored this vintage Champion 90s track jacket and I'm obsessed with how it looks paired with baggy jeans and fresh white sneakers. 👟 It’s giving major retro athletic energy and honestly completes any casual streetwear fit effortlessly. ✨ Snagged this gem for just $45 over on Poshmark before anyone else could grab it.

#ThriftFind #VintageStreetwear #PoshmarkStyle
```

Criterion 5, try 5 (`agent.py::run_agent`, budget $51 → window $50–60):

```
- Input: `vintage under $51`
- selected_item id: lst_036, platform: depop
- search_results prices: [52.0]
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
| 1 | A matching query completes all three tools (original) | 4 of 5 | MET (5/5) | All five tries ended with `error` None and a fit card set. |
| 1 | Revised: …and the selected item's title contains the item word (`tee`) | 4 of 5 | MISSED (0/5) | Scored from the same before run: all five selected "Vintage Graphic Hoodie — Faded Black", which has no "tee" in its title. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five stopped with `fit_card` None and a message naming what to change ("Try without size xxs, or try fewer or different words"). |
| 3 | The chosen item keeps its id through every tool | 5 of 5 | MET (5/5) | In all five, `selected_item`, `search_results[0]` and both `passed_to` entries had the same id, including try 2, which went through the price fallback. |
| 4 | The fit card names where to buy the item | 4 of 5 | MET (5/5) | All five captions contained their listing's platform. Try 4 named Poshmark only in its last sentence, which still counts. |
| 5 | Search results stay inside the budget's price window | 5 of 5 | MET (5/5) | Every price in every try was inside its window, and each try returned at least one listing (the $51 try returned one, at $52). |

**Diagnoses**

**The one miss: revised criterion 1 (0 of 5).**

- *Place:* a tool, `search_listings` (`tools.py`), in the price filter, not
  the ranking.
- *Mechanism:* a budget of $30 sets the $10 window $25–35 (round up to the
  next 5, subtract 5). The shop has three tees (Baby Tee $18, Band Tee $19,
  Graphic Tee $24), and all three are below $25, so the filter removes them
  before anything is scored. Of what's left in $25–35, "Vintage Graphic Hoodie"
  has two query words in its title ("vintage", "graphic") and wins the
  ranking. The ranking itself works: the same search with no price returns
  the Band Tee and the Graphic Tee as the top two. The window's bottom edge
  is the problem. A user who says "under $30" means anything up to $30, and
  my rule throws away everything cheaper than $25, the exact items they'd be
  happiest with.
- *Why no other criterion caught it:* criterion 5 checks that results stay
  inside the window, so it passes precisely because the window is applied.
  The window rule and criterion 5 agree with each other; the rule just
  doesn't match what "under" means.

**A pattern in the other observations.** The same run showed the keyword
search treating every query word as equal: the Low-Rise Cargo Pants match
"tee" only because their description says "a long tee", and in earlier
manual runs `'black boots'` returned black biker shorts because the shop has
no boots and "black" alone was enough. That's the same mechanism in the
ranking step: an item word ("tee", "boots") counts no more than a colour or
style word. It didn't cause the miss above, but it's the next thing I'd fix.

One smaller finding from the run log: the stop message prints "size xxs" in
lowercase. `agent.py::_stop_message` builds the tips and then calls
`.capitalize()` on the whole string, which lowercases everything after the
first letter. The message still names what to change, so criterion 2 passes,
but the size reads wrong.

**Targets that were set too low.** Criteria 1 and 4 targeted 4 of 5 and
both scored 5 of 5.

- *Criterion 4 → 5 of 5.* I allowed one slip because the caption comes from
  the model at temperature 0.9, but the prompt names the platform outright
  ("Mention the item, the price ($24) and the platform (depop) once each"),
  and in the before run and every manual run in unit 3 it never left it out.
  5 of 5 is the honest target.
- *Criterion 1 (original) → 5 of 5 for completion.* The 4 of 5 was there for
  model outages, and those are real: two 503 "high demand" errors happened
  during manual testing. But since the unit 4 handler, an outage ends the run
  with a clear message instead of a crash, so "completes" could fairly be
  required 5 of 5 on a run with no outage, with outages reported separately.

**Revision.** Criterion 1 is revised in `criteria.md` with the original line
left in place. It's revised because it measured the wrong thing (it passed
while the user got a hoodie for a tee), not because it was missed. The
original was met 5 of 5.


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
$ python app.py ask 'denim jacket under $50' --trace
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', max_price=50.0, num_outfits=2
[2] search_listings (via MCP)
      in:  description='denim jacket', max_price=50.0
      out: 1 items: 90s Track Jacket — Navy/White Stripe
      →    branch: results found → select
[3] select
      out: 90s Track Jacket — Navy/White Stripe ($45.0, poshmark)
      →    first result → selected_item
[4] check_owned
      in:  90s Track Jacket — Navy/White Stripe ($45.0, poshmark)
      out: 2 items: Vintage black denim jacket…
[5] suggest_outfit
      in:  item='90s Track Jacket — Navy/White Stripe', wardrobe_items=11, num_outfits=2
      out: 1. 90s Track Jacket — Navy/White Stripe + White ribbed tank top + Baggy straight-leg jeans, dark wash + Chunky…
[6] create_fit_card
      in:  item='90s Track Jacket — Navy/White Stripe', outfit='(from suggest_outfit)'
      out: Scored this vintage Champion navy and white track jacket on Poshmark for just $45, and the retro athletic vibe…
      →    done
```

**Empty search**

```
$ python app.py ask 'tuxedo' --trace
[1] parse_query
      in:  tuxedo
      out: description='tuxedo', num_outfits=2
[2] search_listings (via MCP)
      in:  description='tuxedo'
      out: [] (empty)
      →    branch: empty → stop before suggest_outfit

  Nothing in the shop matches 'tuxedo' at any price. Try fewer or different words.

0 model calls this session
```

The empty search stops after 2 steps and the happy path runs 6, so the branch
is doing its job. Step 2 is the MCP call in both. This trace was recorded
before the improvement: the $50 budget then set a $45–55 window, which is why
the $42 Denim Jacket isn't in it. Since "under" became a ceiling, the same
query selects the Denim Jacket (see The Improvement).

**The three failure modes, triggered on purpose**

1. *Empty search* (`'tuxedo'`, above): stops before `suggest_outfit` with
   "Nothing in the shop matches 'tuxedo' at any price. Try fewer or different
   words." 0 model calls.
2. *Empty wardrobe* (`python app.py ask 'striped polo shirt' --empty-wardrobe`):
   no crash and no empty string.

   ```
     Found:    Vintage Polo Shirt — Forest Green — $18.0 on thredUp

     Outfit:   Your wardrobe is empty, so these use everyday basics:
   1. Pair the forest green polo with straight-leg light wash jeans, white canvas sneakers, and a simple leather belt for a classic casual look.
   2. Layer the polo unbuttoned over a plain white t-shirt, paired with relaxed black trousers and retro low-profile sneakers for an earth-toned casual outfit.
   ```
3. *Model unavailable.* Before the fix, this escaped the loop:
   `ModelUnavailable: Couldn't reach the model: 503 UNAVAILABLE. {'error': ...}`.
   It was caught only by `app.py`'s catch-all, and the item the search had
   already found was thrown away. I added a handler in `agent.py::run_agent`
   that catches `ModelUnavailable` (and `MCPError` for the search server),
   keeps the found item, and says what broke and what to do. With one
   character of the key changed:

   ```
   $ python app.py ask 'olive shacket' --trace
   [1] parse_query ...
   [2] search_listings (via MCP)
         out: 2 items: Shacket — Olive Canvas, Straight Leg Khaki Trousers — Olive
         →    branch: results found → select
   [3] select ...
   [4] check_owned ...
   [5] outfit
         →    model unavailable → stop with a message

     The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. The search still worked: Shacket — Olive Canvas ($33). Try again in a minute.
   ```

   The service also had a real outage (503, "high demand") during testing,
   and the same handler caught it. After that run I removed "Try again in a
   minute" from the bad-key message (waiting doesn't fix a key) and trimmed
   the raw `{'error': ...}` payload out of the 503 message.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

`search_listings` is registered in `mcp_server.py` with all five inputs from
the Tool Inventory (`description`, `size`, `max_price`, `min_price`, `limit`)
and a description written for an agent that can't see the code. Its most
important line says `max_price` is not a ceiling but a $10 window. The server
wraps the real function from `tools.py` and has no search logic of its own.
`python mcp_client.py` lists the tool with those five inputs.

In `agent.py`, the direct import of `search_listings` is replaced by a
same-named function that calls `call_tool("search_listings", {...})`, so all
three searches in the loop (the normal search, the price fallback and
"something new") now go through the server.

Nothing behaved differently. I compared the direct call and the MCP call on
seven searches (a budget window, a custom range, a size, `limit=None`, and the
empty `'tuxedo'`), and all seven came back identical, including `[]` for no
match and `brand: None` surviving the trip as JSON null. `'pink shirt in 10$'`
still takes the fallback and styles the $18 polo. The one cost is speed: each
call starts the server, adding about half a second per search.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One thing, in `agent.py::parse_query`. "under $30" (or
below, less than, up to, max) is now read as a ceiling and passed to
`search_listings` as the range $0–30 (`min_price=0.0, max_price=30.0`). A bare
budget, "$30" or "in 30$", is unchanged: it still becomes `max_price` alone, so
`search_listings` still applies the $10 window. `search_listings` and the
window rule itself are not touched.

**Which failure it was meant to fix:** revised criterion 1, MISSED 0/5. The
diagnosis found that "under $30" became the window $25–35, which filtered out
all three tees ($18, $19, $24) before ranking, so a hoodie won. The ranking
was fine: with no price the tees came first. The fault was in what "under"
was turned into, and the parser is where that happens.

One test change came with it, and it doesn't change the agent: criterion 5
says "run `search_listings('vintage', max_price=B)`". The before run reached
that through `'vintage under $B'` queries, which used to parse to exactly that
call. After the change they wouldn't (they'd become $0–B ranges), so the
criterion 5 scenario now makes the call the criterion names, directly
(`scenarios.py`, `"kind": "search"`). The prices it returned are identical to
the before run.

### Run Log — After

Run with `python run_eval.py --label after` (5 tries per scenario, caching
off, 35 model calls). Full log: `results/run_2026-10-14_0302_after.md`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1. (revised in unit 4) …and the selected item is a tee | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The chosen item keeps its id through every tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card names where to buy the item | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search results stay inside the budget's price window | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Real output, criterion 1 try 1 (`agent.py::run_agent`, from
`results/run_2026-10-14_0302_after.md`):

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', min_price=0.0, max_price=30.0, num_outfits=2
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', min_price=0.0, max_price=30.0
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Vintage Graphic Hoodie — Faded Black … +7 more
      →    branch: results found → select
[3] select
      out: Vintage Band Tee — Faded Grey ($19.0, depop)
      →    first result → selected_item
```

**Did it help, and how do I know:** Yes. Revised criterion 1 went from 0 of 5
to 5 of 5. In the before log every try selected "Vintage Graphic Hoodie —
Faded Black" ($26). In the after log every try selected "Vintage Band Tee —
Faded Grey" ($19), and the Graphic Tee ($24) is second. The other four
criteria stayed at 5 of 5, so nothing regressed. Criterion 5's prices are the
same list for all five budgets, which shows the window rule still works
wherever it's still used.

Two other paths changed in criterion 3's runs, both for the better and both
still passing: `'denim jacket under $50'` now selects the Denim Jacket ($42)
instead of the Track Jacket, and `'silk slip dress under $40'` now finds the
Silk Slip Dress ($30) directly instead of falling back to a Silk Button-Down.
The fallback is still exercised by `'pink shirt in 10$'` (a bare budget).

The trade-off: the window existed so a user would also see things a few
dollars over budget. With "under", they no longer do. I think that matches
what "under" means, but a user who wanted that flexibility now has to write a
bare "$30".



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
