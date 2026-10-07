# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->
My search is plain keyword matching, so a phrasing like "t-shirt" instead of
"tee" can find nothing and stop the run before the other tools. On top of that,
`suggest_outfit` and `create_fit_card` both call the model, and a model call can
fail or come back odd, so one bad run in five is realistic.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->
The stop only happens when no listing has a query word in its title at any
price, and deciding to stop is a plain empty-list check in `run_agent`. No
model call happens on this path, so unlike criterion 1 nothing can vary
between runs, and it should stop all 5 times.

---

## 3. The chosen item keeps its id through every tool

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

Run five queries that each match at least one listing. In each run, the `id`
of `session["selected_item"]` is the same as the `id` of the item the loop
chose from the search (the first result, or the cheapest in the fallback
branch), and the item dict passed to `suggest_outfit` and to `create_fit_card`
has that same `id` — 5 of 5 runs.

**Why this target:** Every listing has a unique `id`, like a bag tag at
check-in. The loop saves the chosen item once in `session["selected_item"]`
and both tools read it from there. No model call touches the item or its `id`,
so passing it along is plain code and should never swap it. A mismatch would
mean the outfit was made for a different item, which the caption alone
wouldn't reveal.


---

## 4. The fit card names where to buy the item

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

Call `create_fit_card('baggy jeans and white sneakers', item)` once for each of
five listings covering all three platforms: `lst_006` (depop), `lst_003` and
`lst_010` (thredUp), `lst_004` and `lst_011` (poshmark). A caption passes if it
names that listing's own `platform` (case doesn't matter) — in at least 4 of 5
captions.

**Why this target:** The platform is the one detail a caption can't do without:
it tells the reader where to buy the item, and once they know that they can
check the price themselves. It's 4 of 5 and not 5 of 5 because the caption
comes from a model call at temperature 0.9, so even with the platform in the
prompt the model can drop a detail now and then.


---

## 5. Search results stay inside the budget's price window

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

Run `search_listings('vintage', max_price=B)` for five budgets: $22, $33, $38,
$45 and $51. Each try passes only if it returns at least one listing and every
returned price is inside that budget's window:

| Budget | Window (inclusive) |
|---|---|
| $22 | $20–30 |
| $33 | $30–40 |
| $38 | $35–45 |
| $45 | $40–50 |
| $51 | $50–60 |

Target: 5 of 5 budgets.

**Why this target:** When shopping, a user is happy with results a few dollars
around their budget and doesn't mind spending $5–10 more for the right piece,
so the search shows a $10 window instead of a hard ceiling. The target is 5 of
5 because `search_listings` doesn't call the model: the window is plain math on
the price, so the same budget gives the same result every time, and even one
miss means the rule is coded wrong.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
