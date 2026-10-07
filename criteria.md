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

4 of 5 because search is plain keyword overlap with no synonyms, so "t-shirt"
won't find a listing titled "tee" and some phrasings will miss.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**

5 of 5 because that path is an if on an empty list with zero model calls;
nothing can vary, so a miss would be a real bug.

---

## 3. The item search found is the item suggest_outfit received

Given the query `'platform sneakers size 8'` run with the example wardrobe, the
id in `session["selected_item"]` equals the id logged for the `suggest_outfit`
call in `session["tool_calls"]` — in 5 of 5 tries.

One try = one run of `run_agent(query, get_example_wardrobe())`, checked with:

    python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; s = run_agent('platform sneakers size 8', get_example_wardrobe()); print(s['selected_item']['id'], s['tool_calls'][1]['inputs']['new_item'])"

**Why this target:**

Everything between the search and `suggest_outfit` is plain Python — the loop
takes `search_results[0]`, stores it in `session["selected_item"]`, and reads
that same key back out for the next call. No model, nothing random, and the
search itself scores the same listings file the same way every run. So the same
query has to produce the same item every time. A run that came back with a
different id wouldn't be bad luck, it would mean the session is dropping or
overwriting state — which is exactly the failure this criterion exists to
catch, so 4 of 5 would be letting a real bug pass.

---

## 4. The fit card names the price and the platform

Running the query `'platform sneakers size 8'` five times with the cache off,
5 of 5 fit cards contain both `$48` and the word `poshmark` (case doesn't
matter).

One try = one run of:

    AI201_CACHE=0 python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; s = run_agent('platform sneakers size 8', get_example_wardrobe()); i = s['selected_item']; print('NEEDS:', '\$' + format(i['price'], '.0f'), i['platform']); print('CARD:', s['fit_card'])"

**Why this target:**

Unlike criterion 3, this one can vary: `TEMPERATURE = 0.9` in config.py means
the model rewrites the caption from scratch every run, and the cache is off so
all five are real calls. I still set 5 of 5 because the prompt in
`create_fit_card` names the price and the platform explicitly, and a caption
that leaves out either one fails at the only job it has — telling someone where
to buy the thing and what it costs. A caption I'd have to edit before posting
is a caption the tool didn't finish, so I'd rather miss this target in unit 4
and have something concrete to fix than set it where I can't fail.

---

## 5. An empty wardrobe produces advice without inventing a closet

Running `'denim jacket under $50'` with `--empty-wardrobe` five times with the
cache off, 5 of 5 runs return a non-empty fit card, and none of the five outfit
suggestions contains any of these five item names from `example_wardrobe` in
`data/wardrobe_schema.json` (case doesn't matter):

- "Baggy straight-leg jeans, dark wash"
- "Oversized grey crewneck sweatshirt"
- "Black cropped zip hoodie"
- "Vintage black denim jacket"
- "Wide-leg khaki trousers"

One try = one run of:

    AI201_CACHE=0 python app.py ask 'denim jacket under $50' --empty-wardrobe

**Why this target:**

The `if not items:` branch in `suggest_outfit` sends the model only the listing
and a request for outfits built from common basics — the wardrobe item names
never enter the prompt, and `_STYLIST` tells it never to invent pieces the user
didn't list. I count only these five of the ten names because the other five
("Black combat boots", "Chunky white sneakers", "White ribbed tank top",
"Brown leather belt", "Black crossbody bag") are ordinary basics a stylist
would suggest unprompted, so finding one would prove nothing. These five stack
two or three modifiers with a specific wash or color, so the model producing
one would mean the example wardrobe reached a prompt that should never have
had it. That makes 5 of 5 honest for the same reason as criterion 3 rather
than criterion 4: a failure here isn't the model varying its wording, it's the
wrong data reaching the prompt.

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
