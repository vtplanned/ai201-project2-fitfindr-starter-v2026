"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    listings = load_listings()

    wanted_size = _size_tokens(size) if size and size.strip() else None
    terms = _keywords(description)
    if not terms:
        return []

    scored = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if wanted_size is not None and not _size_matches(wanted_size, listing["size"]):
            continue

        score = _score(terms, listing)
        if score > 0:
            scored.append((score, listing))

    # Highest score first; cheaper listing wins a tie.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── search helpers ────────────────────────────────────────────────────────────

# Words that say nothing about the item. Dropping them keeps "a tee for me"
# from matching every description that contains "for".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to", "my",
    "me", "i", "im", "want", "need", "looking", "find", "some", "something",
    "that", "this", "is", "it", "size", "under", "below", "less", "than", "max",
    "up", "around", "about", "cheap", "please", "like", "would", "go", "goes",
}


def _normalize(word: str) -> str:
    """Lowercase and drop a plural 's' so 'jeans' and 'jean' match each other."""
    word = word.lower()
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def _words(text: str) -> list[str]:
    return [_normalize(w) for w in re.findall(r"[a-z0-9]+", text.lower())]


def _keywords(description: str) -> list[str]:
    """The distinct search terms in a description, in order, stopwords removed."""
    seen = []
    for word in _words(description or ""):
        if word not in _STOPWORDS and word not in seen:
            seen.append(word)
    return seen


def _score(terms: list[str], listing: dict) -> int:
    """
    Keyword overlap. Each distinct term matched is worth 10, plus 3 if it is in
    the title, 2 if it is in the style tags, category, colors or brand, and 1
    if it is only in the free-text description. A listing matching more of the
    words always outranks one matching fewer.
    """
    title = set(_words(listing["title"]))
    strong = set(_words(" ".join([
        listing["category"],
        " ".join(listing["style_tags"]),
        " ".join(listing["colors"]),
        listing["brand"] or "",
    ])))
    weak = set(_words(listing["description"]))

    score = 0
    for term in terms:
        if term in title:
            score += 13
        elif term in strong:
            score += 12
        elif term in weak:
            score += 11
    return score


def _size_tokens(size: str) -> set[str]:
    """
    Split a size into whole tokens: "S/M" → {"s", "m"}, "US 8.5" → {"us", "8.5"},
    "XL (oversized)" → {"xl", "oversized"}. Matching whole tokens is what stops
    "l" from matching "xl" and "s" from matching "us 9".
    """
    return {t for t in re.split(r"[\s/(),]+", size.lower()) if t}


def _size_matches(wanted: set[str], listing_size: str) -> bool:
    """
    A listing matches when any requested size token equals one of its size
    tokens, ignoring "us" (so "8" matches "US 8" but not "US 8.5"). A "One Size"
    listing matches any request.
    """
    have = _size_tokens(listing_size)
    if "one" in have and "size" in have:
        return True
    return bool((wanted - {"us"}) & (have - {"us"}))

# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    if not new_item:
        return "No item to style — suggest_outfit needs a listing dict."

    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            "They haven't told us anything about their wardrobe. Suggest two "
            "outfits built around this piece using common basics most people "
            "own (say what kind of bottoms, shoes and layers). Keep it to two "
            "short bullet points."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({', '.join(w.get('colors') or [])}; "
            f"{', '.join(w.get('style_tags') or [])})"
            + (f" — note: {w['notes']}" if w.get("notes") else "")
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            f"Here is what they already own:\n{closet}\n\n"
            "Suggest two outfits that pair the new piece with specific items "
            "from their wardrobe. Name the wardrobe pieces exactly as listed. "
            "Keep it to two short bullet points."
        )

    response = generate(prompt, system=_STYLIST)
    if response.strip():
        return response
    return f"Pair the {new_item['title']} with simple basics in neutral colors."

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "No fit card — there was no outfit suggestion to write about."

    brand = f"Brand: {new_item['brand']}\n" if new_item.get("brand") else ""
    prompt = (
        f"Item: {new_item['title']}\n"
        f"{brand}"
        f"Price: ${new_item['price']:.0f}\n"
        f"Platform: {new_item['platform']}\n"
        f"Condition: {new_item['condition']}\n\n"
        f"How they'll wear it:\n{outfit}\n\n"
        "Write the caption for an outfit post about this thrift find. Two to "
        "four sentences, first person, casual, like a real Instagram or TikTok "
        "caption. Mention the item, the price and the platform once each. Be "
        "specific about the vibe of the outfit. At most two emoji and at most "
        "three hashtags. Return only the caption."
    )
    return generate(prompt, system=_CAPTION_WRITER)


# ── model helpers ─────────────────────────────────────────────────────────────

_STYLIST = (
    "You are a practical personal stylist for someone who shops secondhand. "
    "Be concrete and brief. Never invent wardrobe items the user didn't list."
)

_CAPTION_WRITER = (
    "You write short social media captions for thrift finds. Sound like a "
    "person, not a product listing."
)


def _describe_item(item: dict) -> str:
    """One listing as a few readable lines for a prompt. Brand is often None."""
    lines = [
        f"{item['title']} — ${item['price']:.0f} on {item['platform']}",
        f"Category: {item['category']}; size {item['size']}; condition {item['condition']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Seller's description: {item['description']}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)