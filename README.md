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

**Moment 3 — unit 4, checking whether my "before" run actually proved anything**

- *What I asked for:* After `run_eval.py --label before` came back 5/5 on every criterion, I asked Claude whether a perfect score across the board meant my agent was actually solid, given that criterion 1's own reasoning names a known weakness (keyword search with no synonyms).
- *What came back:* It pointed out that criterion 1's scenario runs the identical query `'vintage graphic tee under $30'` five times against a deterministic, non-model function — so five identical inputs can only ever produce five identical outputs, regardless of whether the search actually handles paraphrasing. It then ran `search_listings('t-shirt')` directly and showed it returned zero of the three Tee-titled listings, because `"t-shirt"` tokenizes into `"t"` and `"shirt"`.
- *What I changed:* Claude gave me the raw facts (the scenario reruns one fixed query, and the tokenization behind the miss) without the conclusion, and asked me to connect them myself before writing anything. I wrote the Diagnoses and Improvement reasoning above from that; the regex fix in `tools.py::_words` folds `t-shirt`/`t shirt`/`tshirt` onto `tee` before tokenizing, and I confirmed `search_listings('shirt')` still only matches Shirt-titled listings.

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
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item suggest_outfit received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card names the price and the platform | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. An empty wardrobe produces advice without inventing a closet | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Full output for all 25 tries is in `results/run_2026-10-13_2352_before.md`
(`run_eval.py::main`, caching off). One try per criterion, pasted as text:

**Criterion 1** — `agent.py::run_agent('vintage graphic tee under $30', example wardrobe)`, try 1:

```
selected_item: Vintage Band Tee — Faded Grey ($19.0, depop)
outfit: * **Outfit 1:** Vintage Band Tee tucked into Baggy straight-leg jeans, dark wash, worn with Black combat boots and the Black crossbody bag.
* **Outfit 2:** Vintage Band Tee layered over the White ribbed tank top, paired with Wide-leg khaki trousers, Chunky white sneakers, and the Black cropped zip hoodie worn unzipped on top.
fit_card: Found this insanely faded grey vintage band tee and knew I had to style it. Got it on Depop for just $19, and honestly, it looks so good layered with the white tank, khaki trousers, and a zip hoodie for that ultimate grunge-meets-casual look. 🖤

#thrifted #depopfinds #vintagestyle
```

**Criterion 2** — `agent.py::run_agent('designer ballgown size XXS under $5', example wardrobe)`, try 1:

```
stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches the words 'designer ballgown' at any size or price — try different words for the item, like the kind of piece (tee, jacket, jeans, boots) or a style (vintage, 90s, y2k, streetwear).
selected_item: (none)
search_results: 0
```

**Criterion 3** — `agent.py::run_agent('platform sneakers size 8', example wardrobe)`, run directly five times with the check from `criteria.md`:

```
$ python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; s = run_agent('platform sneakers size 8', get_example_wardrobe()); print('selected_item.id =', s['selected_item']['id']); print('suggest_outfit got new_item =', s['tool_calls'][1]['inputs']['new_item'])"

selected_item.id = lst_019
suggest_outfit got new_item = lst_019
```

Ran 5 of 5 times — same output every time.

**Criterion 4** — `tools.py::create_fit_card`, via `agent.py::run_agent('platform sneakers size 8', example wardrobe)`, try 1:

```
Y'all know I couldn't pass up these chunky white platform sneakers when I spotted them on Poshmark for just $48. I've been living in them with my dark indigo baggy jeans, a ribbed tank, and an oversized black denim jacket for that ultimate off-duty look. 👟✨

#thrifted #streetwear #poshmarkfinds
```

Contains `$48` and `Poshmark` — checked across all five tries, same result each time.

**Criterion 5** — `tools.py::suggest_outfit`, via `agent.py::run_agent('denim jacket under $50', empty wardrobe)`, try 1:

```
* **Casual Daytime:** Pair with a white t-shirt tucked into black straight-leg jeans, and white canvas sneakers.
* **Elevated Casual:** Layer over a black ribbed tank top with a pleated midi skirt and leather ankle boots.
```

None of the five distinctive wardrobe names appear in any of the five tries.

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
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All five tries returned a non-`None` `selected_item`, outfit suggestion, and fit card, with `session["error"]` staying `None` throughout. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | All five tries set `session["error"]` after `search_listings` returned `[]`, and `fit_card` stayed `None` — `suggest_outfit` never ran. |
| 3 | The item search found is the item suggest_outfit received | 5 of 5 | MET (5/5) | Ran the exact check named in the criterion five times; `selected_item["id"]` and `tool_calls[1]["inputs"]["new_item"]` were both `lst_019` every time. |
| 4 | The fit card names the price and the platform | 5 of 5 | MET (5/5) | All five fit cards contained the literal substrings `$48` and `poshmark` (case-insensitive). |
| 5 | An empty wardrobe produces advice without inventing a closet | 5 of 5 | MET (5/5) | None of the five outfit suggestions contained any of the five distinctive wardrobe item names, checked by literal substring. |

**Diagnoses**

Criterion 1 ran `'vintage graphic tee under $30'` five times and passed 5/5,
but that result only shows the agent is consistent, not that it's correct —
every try sent the exact same query through a tool with zero randomness, so
five passes and one pass are the same evidence. Checking `search_listings`
directly with a different phrasing exposed the gap the repeated-query test
couldn't: `search_listings('t-shirt')` returned none of the three "Tee"
listings while `search_listings('tee')` returned all three, because the
hyphen in "t-shirt" splits it into the tokens `"t"` and `"shirt"`, which only
scores against titles containing "Shirt." The run log's 5/5 was real, but it
was testing the same input five times rather than testing five different
inputs once each — a passing score that happened to miss the actual failure
mode.

**Target I'd tighten:** criterion 1's scenario, not its number. Testing the
same query five times can't distinguish "the search handles paraphrasing" from
"the search was never asked to." A scenario that actually probes the 4-of-5
target would run five different, real phrasings of the same item and budget —
"tee" vs "t-shirt" vs "graphic tee" — so a miss like this one would show up in
the run log instead of requiring a separate check to find it.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'vintage graphic tee under $30' --trace`

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print … +7 more
[3] select
      out: Vintage Band Tee — Faded Grey ($19.0, depop)
[4] suggest_outfit
      in:  dict with keys: new_item, wardrobe_items
      out: * Pair the Vintage Band Tee with the Baggy straight-leg jeans, dark wash, Black combat boots, and Black crossb…
[5] create_fit_card
      in:  dict with keys: new_item
      out: Found this perfectly faded grey band tee on Depop for just $19 and I'm obsessed. I've been living in it with b…
```

**Empty search** — `python app.py ask 'designer ballgown size XXS under $5' --trace`

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
[3] stop_empty
      →    branch: empty, stopping — No listings matched 'designer ballgown' in size XXS under $5. Nothing in the listings matches the words 'designer ballgown' at any size or price — try different words for the item, like the kind of piece (tee, jacket, jeans, boots) or a style (vintage, 90s, y2k, streetwear).
```

The empty path stops at step 3; the happy path runs all five. That's the
branch working — the MCP call is step 2 in both, and the loop doesn't reach
`suggest_outfit` or `create_fit_card` when there's nothing to style.

**On the MCP move:** `search_listings` is the tool I moved — it's the one that
doesn't call the model, so nothing about its behavior should change based on
transport. In `mcp_server.py` I registered it with its name, a description
written for a reader who can't see the code (units on the price, what "size"
matches, the empty-list case), and the typed inputs straight from my Tool
Inventory. In `agent.py::run_agent`, the direct `search_listings(...)` call
became `call_tool("search_listings", {...})`, and the diagnostic re-searches
inside `_no_results_message` were switched the same way, so every path that
used to call the tool directly now goes through MCP. The return value didn't
change shape — same list of listing dicts, same empty-list case — which is
what the milestone said should happen when the move is done right.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

Since the bug is that "t-shirt" tokenizes away from "tee" instead of toward
it, the fix folds t-shirt, tshirt, and t shirt onto tee before the description
is tokenized (`tools.py::_words`), so a query using any of those phrasings
scores against the same listings a plain "tee" query would.

**Which failure it was meant to fix:**

The tokenization gap found in the diagnosis above — `search_listings('t-shirt')`
matched none of the three Tee-titled listings beforehand, because the hyphen
split it into `"t"` and `"shirt"` instead of something that scores against
"Tee."

### Run Log — After

Full output for all 25 tries is in `results/run_2026-10-13_2358_after.md`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item suggest_outfit received | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card names the price and the platform | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. An empty wardrobe produces advice without inventing a closet | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:**

The five formal criteria were already 5/5 before and after — this change
wasn't aimed at them, since their scenarios never exercised the gap in the
first place (that's the whole diagnosis above). What it fixed is the specific,
reproducible miss I found by testing the risk directly:

```
$ python -c "from tools import search_listings; print([l['title'] for l in search_listings('t-shirt')])"

Before: []
After:  ['Y2K Baby Tee — Butterfly Print', 'Vintage Band Tee — Faded Grey', 'Graphic Tee — 2003 Tour Bootleg Style', 'Mesh Long-Sleeve Top — Black', 'Low-Rise Cargo Pants — Khaki']
```

I checked it didn't cost anything elsewhere: `search_listings('shirt')` still
returns only the Shirt-titled listings (Polo Shirt, Flannel Shirt, Shacket),
unchanged — the substitution only fires on `t-shirt`/`t shirt`/`tshirt`, not
on "shirt" alone. `python test.py` still passes 10/10 after the change.

So: it helped, on the thing it was meant to help with, and it's the kind of
fix a scenario change alone couldn't have validated — varying the wording in
criterion 1's test would have *revealed* this miss, but only a code change to
`tools.py` could fix it.



---

## What's Still Broken

No criterion missed, before or after. What's still open is the test-design gap
named in the diagnosis: criterion 1's scenario runs the same query five times,
so it can't actually detect a phrasing-dependent miss on its own — I only
found the `t-shirt`/`tee` gap by testing `search_listings` directly, outside
`run_eval.py`. The fix for *that* item (the criterion I'd tighten) would mean
changing `scenarios.py` to run five different real phrasings of the same
item/budget for criterion 1 instead of one repeated query, so a future miss
like this one shows up in the formal run log instead of requiring a separate
check to surface it. I didn't do that this unit because the rule here is one
change, and I'd already used it on the actual code fix in `tools.py` — but it's
the next thing I'd do before trusting this test suite further.

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
