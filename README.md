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

FitFindr is a command-line agent for thrift shopping. You type what you want in
plain language — `vintage graphic tee under $30, size M` — and it searches 40
secondhand listings from Depop, thredUp and Poshmark, filtering on your size and
price ceiling. It picks the best match, suggests two outfits that pair it with
pieces from your wardrobe (or general styling ideas if your wardrobe is empty),
and writes a short caption you could post with the fit. If nothing matches, it
stops before calling the model and tells you which part of your request to
change — the words, the size, or the price.


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

- **What it does:** Filters `data/listings.json` by price and size, then ranks what's left by keyword overlap with the description. No model call.
- **Inputs:** `description` (str) — keywords like `"vintage graphic tee"`; `size` (str or None) — e.g. `"M"`, `"8"`, `None` skips the size filter; `max_price` (float or None) — inclusive ceiling, `None` skips it.
- **Returns:** A `list[dict]` of up to 10 listing dicts (`config.SEARCH_RESULT_LIMIT`), best match first. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
  - *Scoring:* each distinct query word found adds 10, plus 3 if it's in the title, 2 if in style tags/category/colors/brand, 1 if only in the description. Stopwords ("a", "for", "under"…) are ignored and plural "s" is dropped. Ties go to the cheaper listing. Listings scoring 0 are dropped.
  - *Size match:* sizes are split into whole tokens on spaces, `/` and parentheses, so `"M"` matches `"S/M"`, `"M/L"` and `"M"`; `"L"` does **not** match `"XL"`; `"8"` matches `"US 8"` but not `"US 8.5"`; `"S"` does not match `"US 9"`. Listings sized "One Size" match any requested size.
- **When it has nothing:** An empty list `[]` — never `None`, never an exception. That includes a description made only of stopwords.

### `suggest_outfit`

- **What it does:** Asks the model for two outfit ideas built around the new item, using pieces from the user's wardrobe by name.
- **Inputs:** `new_item` (dict) — one listing dict, as returned by `search_listings`; `wardrobe` (dict) — `{"items": [...]}` where each item has `id`, `name`, `category`, `colors`, `style_tags`, `notes`.
- **Returns:** A non-empty `str` of two bullet-point outfits that name wardrobe items exactly as listed.
- **When it has nothing:** If `wardrobe["items"]` is empty, it still returns a `str` — two outfits using common basics (general advice) instead of named wardrobe pieces. If `new_item` is empty/None it returns the string `"No item to style — suggest_outfit needs a listing dict."` If the model returns blank text, it returns a one-line fallback suggestion. It never returns `""`.

### `create_fit_card`

- **What it does:** Asks the model for a 2–4 sentence, first-person social caption that mentions the item, its price and its platform once each, with at most two emoji and three hashtags.
- **Inputs:** `outfit` (str) — the string from `suggest_outfit`; `new_item` (dict) — the same listing dict. Brand is only put in the prompt when it isn't `None`.
- **Returns:** A `str` caption. Runs at `TEMPERATURE = 0.9`, so the same input gives different wording each run (with the cache off).
- **When it has nothing:** If `outfit` is empty or only whitespace, it returns `"No fit card — there was no outfit suggestion to write about."` without calling the model.

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

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what to change (different words, a higher max price with the cheapest matching price, or a different size with the sizes that exist) and return the session — `suggest_outfit` and `create_fit_card` are never called and `fit_card` stays `None`. Otherwise, put the first result in `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent` — the loop calls `agent.py::_next_step`, which looks at the session and returns `"stop_empty"` when `session["search_results"]` is empty. The message comes from `agent.py::_no_results_message`.

**How the loop works:** `run_agent` is a `while` loop. Each pass it calls `trace.check_iterations(count)` (stop condition, `MAX_ITERATIONS = 10`), then asks `_next_step(session)` what to do based on what the session holds so far: `parse` → `search` → (`stop_empty` **or** `select`) → `suggest` → `fit_card` → `done`.

**How the query is parsed:** Regex, in `agent.py::parse_query`. It pulls out a price (`under $30`, `below 30 bucks`, `$30`), a size (`size M`, `in size 8`), strips lead-ins like "looking for", and what's left is the description. Example: `"vintage graphic tee under $30, size M"` → `{"description": "vintage graphic tee", "size": "M", "max_price": 30.0}`.

**What moves through the session:** `query` → `parsed` (description/size/max_price) → `search_results` (list from `search_listings`) → `selected_item` (`search_results[0]`) → `outfit_suggestion` (from `suggest_outfit`, which reads `selected_item` and `wardrobe` from the session) → `fit_card` (from `create_fit_card`, which reads `outfit_suggestion` and `selected_item` from the session). Every tool call is also logged in `session["tool_calls"]` with its inputs (including the item `id` passed to `suggest_outfit`), so you can check the item that reached each tool is the one search found. On the empty path, `error` is set and the later fields stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   * **Outfit 1:** Y2K Baby Tee + Baggy straight-leg jeans (dark blue, indigo; denim, streetwear, baggy) + Chunky white sneakers (white; sneakers, chunky, streetwear) + Black crossbody bag (black; minimal, accessories, everyday)
* **Outfit 2:** Y2K Baby Tee + Wide-leg khaki trousers (khaki, tan; earth tones, minimal, wide-leg) + Vintage black denim jacket (black; denim, vintage, classic) + Black combat boots (black; boots, grunge, classic)

  Fit card: Channeling major 2000s mall vibes with this little butterfly tee, paired with oversized indigo denim and chunky kicks for everyday streetwear. Found this mint-condition baby tee for just $18 on Depop, and honestly it’s too good to gatekeep. 🦋 

#y2k #thriftfinds #depop

2 model calls this session, 615 prompt + 188 output tokens
```

**The empty branch** — a query nothing can match stops before any model call:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches the words 'designer ballgown' at any size or price — try different words for the item, like the kind of piece (tee, jacket, jeans, boots) or a style (vintage, 90s, y2k, streetwear).

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

Empty case:

```
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
* Pair the Vintage Levi's 501 Jeans with the White ribbed tank top, Black cropped zip hoodie, and Chunky white sneakers.
* Pair the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt and Black combat boots, using the Brown leather belt.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Finally found the holy grail of denim with these vintage Levi's 501s and honestly, they fit like a dream. Just tossed them on with some beat-up white sneakers for that effortlessly cool 90s running-errands vibe. Grabbed them on depop for $38 and I'm never taking them off. 👖✨

#thrifted #levis #depopfinds
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1 — attacking my empty-wardrobe criterion (criterion 5)**

- *What I asked for:* I gave Claude my draft of criterion 5 and asked whether someone else could test it from the sentence alone. My first version said the outfit suggestion should "describe generic pieces rather than naming specific items."
- *What came back:* Claude pointed out that the empty-wardrobe prompt in `suggest_outfit` literally asks for "common basics most people own," so the model *will* name pieces like "a white t-shirt" — and a grader can't decide whether that's "generic" or "specific" without asking me. It suggested a yes/no check instead: none of the example wardrobe's item names appear in the outfit. When I rewrote it with all ten names, it flagged a second problem: names like "Black combat boots" and "Chunky white sneakers" are ordinary basics a stylist would suggest anyway, so finding one wouldn't prove the wrong wardrobe reached the prompt.
- *What I changed:* I narrowed the check to the five distinctive names (like "Baggy straight-leg jeans, dark wash"), listed them in the criterion, added "case doesn't matter," and rewrote my reason to explain why the other five don't count.

**Moment 2 — attacking my fit-card criterion (criterion 4)**

- *What I asked for:* I asked Claude to test criterion 4 the same way: "5 of 5 fit cards contain both `$48` and the word `poshmark`."
- *What came back:* It noted that the listings data stores the platform in lowercase (`poshmark`) but the model writes captions like a real post and capitalizes it (`Poshmark`), so a grader reading my sentence literally would fail every correct card over one capital letter. It also checked that `$48.00` would still count, since it contains `$48`.
- *What I changed:* I added "(case doesn't matter)" after `poshmark`. I kept my 5 of 5 target even though the model runs at temperature 0.9, and wrote out why: a caption missing the price or platform isn't one I'd post.

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
