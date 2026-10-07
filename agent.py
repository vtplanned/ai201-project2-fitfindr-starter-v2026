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

import config  # noqa: F401
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


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
        "tool_calls": [],            # every tool run, in order, with what went in
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
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

    count = 0
    while True:
        count += 1
        trace.check_iterations(count)

        step = _next_step(session)

        if step == "parse":
            session["parsed"] = parse_query(query)

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            _record(session, "search_listings", dict(parsed),
                    f"{len(session['search_results'])} results")

        elif step == "stop_empty":
            # THE BRANCH: nothing came back, so there is nothing to style.
            session["error"] = _no_results_message(session["parsed"])
            return session

        elif step == "select":
            session["selected_item"] = session["search_results"][0]

        elif step == "suggest":
            item = session["selected_item"]
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            _record(session, "suggest_outfit",
                    {"new_item": item["id"],
                     "wardrobe_items": len(session["wardrobe"].get("items") or [])},
                    session["outfit_suggestion"])

        elif step == "fit_card":
            item = session["selected_item"]
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            _record(session, "create_fit_card", {"new_item": item["id"]},
                    session["fit_card"])

        else:  # "done"
            return session


def _next_step(session: dict) -> str:
    """
    Look at what the session holds so far and pick the next step. This is the
    planning part: every decision is made from the last result, not from a
    fixed list.
    """
    if not session["parsed"]:
        return "parse"
    if not any(c["tool"] == "search_listings" for c in session["tool_calls"]):
        return "search"
    if not session["search_results"]:
        return "stop_empty"
    if session["selected_item"] is None:
        return "select"
    if session["outfit_suggestion"] is None:
        return "suggest"
    if session["fit_card"] is None:
        return "fit_card"
    return "done"


def _record(session: dict, tool: str, inputs: dict, returned) -> None:
    """Log a tool call in the session, so a test can see what each tool got."""
    session["tool_calls"].append({"tool": tool, "inputs": inputs, "returned": returned})


# ── query parsing (regex) ─────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|max(?:imum)?|up to|<=?|for)\s*\$\s*(\d+(?:\.\d+)?)"
    r"|(?:under|below|less than|up to)\s*(\d+(?:\.\d+)?)\s*(?:dollars|bucks)?"
    r"|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE = re.compile(
    r"\b(?:in\s+)?(?:a\s+)?size\s+((?:us\s*)?[a-z0-9./]+)",
    re.IGNORECASE,
)
_FILLER = re.compile(
    r"^\s*(?:i'?m\s+|i\s+am\s+)?(?:looking\s+for|searching\s+for|find\s+me|i\s+want|i\s+need|show\s+me)\s+",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max price out of plain language with
    regex. "vintage graphic tee under $30, size M" →
    {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}.
    size and max_price are None when the query doesn't give one.
    """
    text = query

    max_price = None
    price_match = _PRICE.search(text)
    if price_match:
        max_price = float(next(g for g in price_match.groups() if g))
        text = text[:price_match.start()] + " " + text[price_match.end():]

    size = None
    size_match = _SIZE.search(text)
    if size_match:
        size = size_match.group(1).strip(" .,")
        text = text[:size_match.start()] + " " + text[size_match.end():]

    text = _FILLER.sub("", text)
    description = " ".join(re.sub(r"[,;]", " ", text).split())

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """
    Say what to change, not just "no results". Re-runs the search with each
    filter dropped to find out which one emptied it.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]

    asked = f"'{desc}'"
    if size:
        asked += f" in size {size}"
    if price is not None:
        asked += f" under ${price:g}"

    message = f"No listings matched {asked}."

    if not search_listings(desc):
        return (
            f"{message} Nothing in the listings matches the words '{desc}' at "
            f"any size or price — try different words for the item, like the "
            f"kind of piece (tee, jacket, jeans, boots) or a style "
            f"(vintage, 90s, y2k, streetwear)."
        )

    hints = []
    if price is not None and search_listings(desc, size, None):
        cheapest = min(l["price"] for l in search_listings(desc, size, None))
        hints.append(f"raise your max price — the cheapest match is ${cheapest:g}")
    if size and search_listings(desc, None, price):
        sizes = sorted({l["size"] for l in search_listings(desc, None, price)})
        hints.append(f"try another size — matches come in {', '.join(sizes[:5])}")
    if not hints:
        hints.append("drop the size or the price limit — together they rule out every match")

    return f"{message} To find something, {' or '.join(hints)}."


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
