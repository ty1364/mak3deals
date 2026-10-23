"""Server-side daily word puzzle for Mak3Deals."""

from datetime import date, datetime, timezone
import re


DAILY_WORDS = [
    "PRICE", "SMART", "SALES", "SHARE", "VALUE", "STORE", "DEALS", "OFFER",
    "CASHY", "COINS", "SAVER", "SPEND", "STACK", "TERMS", "LOCAL", "LOYAL",
    "CARTS", "SHOPS", "CHECK", "BUYER", "SAVED", "WATCH", "MATCH", "CLICK",
    "TODAY", "FLASH", "BONUS", "POINT", "ROUND", "DRIVE",
    "FUNDS", "GOODS", "PERKS", "PROMO", "SCORE", "SHELF", "TOTAL", "CENTS",
    "ADDED", "ALERT", "AWARD", "BILLS", "BRAND", "CARRY", "CLAIM", "CLEAR",
    "CLOSE", "CODES", "COSTS", "DEBIT", "EMAIL", "ENTRY", "EVENT", "EXTRA",
    "FEWER", "FIRST", "FIXED", "FRESH", "HABIT", "ITEMS", "LABEL", "LIMIT",
    "MONEY", "ORDER", "PAIRS", "PAPER", "PLANS", "PRIZE", "QUICK", "RATES",
    "REFER", "RENEW", "SCANS", "SHIPS", "SIZES", "SPREE", "STOCK", "STYLE",
    "TAXES", "TRACK", "TRIAL", "USERS", "WORTH", "YIELD", "ZONES", "BASIC",
    "CHART", "CLASS", "CLEAN", "DAILY", "FAVOR", "GUIDE", "HOMES", "INDEX",
    "ISSUE", "KNOWN", "MAJOR", "NOTED", "PICKS", "PROOF", "RANGE", "RANKS",
    "RECAP", "RIGHT", "SKILL", "SOLID", "STATS", "TRADE", "WEEKS", "WORDS",
    "AISLE", "BULKS", "DELAY", "LOWER", "PENNY", "SAVES", "TOKEN", "TREND",
    "BAGEL", "BATCH", "BREAD", "CHAIR", "CHIPS", "CRAFT", "CRATE", "DAIRY",
    "EARLY", "FINAL", "FLIER", "FRUIT", "GLASS", "GRILL", "JEWEL", "JUMBO",
    "LINEN", "MEALS", "MILES", "MONTH", "NOTES", "PASTA", "PLANT", "PRINT",
    "SAUCE", "SCENT", "SNACK", "STAMP", "SWIPE", "SWEEP", "TALLY", "TILLS",
    "TOOLS", "TOTES",
    "DROPS", "FINDS", "SWAPS", "MARKS", "DEPOT", "POUCH", "UNBOX", "SCOUT",
    "STASH", "WAGON", "BROOM", "SPICE", "BERRY", "LEMON", "MELON", "OLIVE",
    "ONION", "BEANS", "PEACH", "GRAPE", "LUNCH", "CANDY", "SWEET", "CREAM",
    "FROST", "SHEET", "COUCH", "TABLE", "LIGHT", "CABLE", "BRUSH", "APRON",
    "KNIFE", "SPOON", "PLATE", "BLEND",
]

DAILY_HINTS = {
    "PRICE": "It is the number you check before deciding whether something is worth buying.",
    "SMART": "A careful shopper is this.", "SALES": "More than one savings event happening at once.",
    "SHARE": "What you do when you pass a great deal to a friend.", "VALUE": "What you get compared with what you spend.",
    "STORE": "A place or website where people shop.", "DEALS": "Savings opportunities, in the plural.",
    "OFFER": "A retailer's promotion or proposal.", "CASHY": "A playful way to describe something connected to money.",
    "COINS": "Small pieces of money.", "SAVER": "Someone who looks for ways to spend less.",
    "SPEND": "What you do when money leaves your wallet.", "STACK": "What you can do with compatible discounts.",
    "TERMS": "The conditions and restrictions attached to an offer.", "LOCAL": "A deal from a nearby business.",
    "LOYAL": "The kind of customer reward tied to repeat shopping.", "CARTS": "Where online shoppers collect items before checkout.",
    "SHOPS": "Places where people buy things.", "CHECK": "What you should do before paying or publishing a deal.",
    "BUYER": "The person making the purchase.", "SAVED": "What happened when a discount reduced your cost.",
    "WATCH": "What you do to keep an eye on a price.", "MATCH": "A retailer policy that may meet a competitor's price.",
    "CLICK": "The action that opens a deal or retailer link.", "TODAY": "The day this puzzle was published.",
    "FLASH": "A short-lived promotion with limited time.", "BONUS": "An extra reward added to the main savings.",
    "POINT": "A unit in a loyalty or rewards program.", "ROUND": "One cycle of guesses in a game.",
    "DRIVE": "A trip to the store, or motivation to save.",
    "FUNDS": "Money set aside for a purchase.", "GOODS": "Items offered for sale.",
    "PERKS": "Extra benefits attached to a membership or offer.", "PROMO": "A short name for a promotion.",
    "SCORE": "The points you earn in a game or the value of a deal.", "SHELF": "Where a product waits in a store.",
    "TOTAL": "The final amount before or after savings are applied.", "CENTS": "The smaller units that make up a dollar.",
    "AISLE": "A passage between shelves where shoppers walk.", "BULKS": "Large quantities bought or sold together.",
    "DELAY": "A wait before an order, sale, or delivery happens.", "LOWER": "What a retailer may do to a price.",
    "PENNY": "One cent in U.S. currency.", "SAVES": "Reduces what someone has to spend.",
    "TOKEN": "A small item or unit that can represent value or access.", "TREND": "A pattern in prices, products, or shopping behavior.",
    "BAGEL": "A ring-shaped bakery item that may appear in a grocery deal.",
    "BATCH": "A group of offers gathered together for shoppers to review.",
    "BREAD": "A grocery staple often featured in weekly store promotions.",
    "CHAIR": "A piece of furniture shoppers may compare across stores.",
    "CHIPS": "A crunchy snack that commonly appears in multi-buy offers.",
    "CRAFT": "A hobby category where shoppers look for materials and kits.",
    "CRATE": "A sturdy container used to carry or organize purchases.",
    "DAIRY": "The grocery section for milk, yogurt, and related foods.",
    "EARLY": "The time some members can access a promotion before others.",
    "FINAL": "The price left after every eligible discount is applied.",
    "FLIER": "A printed or digital weekly advertisement from a store.",
    "FRUIT": "Fresh produce that often features in grocery specials.",
    "GLASS": "A material used for drinkware and some household products.",
    "GRILL": "Outdoor cooking equipment shoppers may seek during seasonal sales.",
    "JEWEL": "A precious stone or a small item sold by a jewelry retailer.",
    "JUMBO": "A size label that signals a larger-than-standard package.",
    "LINEN": "A home-textile category that includes sheets and table cloths.",
    "MEALS": "Prepared or planned food purchases for the week.",
    "MILES": "A travel-rewards unit that can help reduce a future trip cost.",
    "MONTH": "A calendar period used to organize recurring promotions.",
    "NOTES": "Paper money, or reminders a shopper keeps while comparing offers.",
    "PASTA": "A pantry staple that may be discounted in grocery aisles.",
    "PLANT": "A garden or houseplant purchase found in seasonal offers.",
    "PRINT": "How a shopper can produce a paper coupon from an authorized source.",
    "SAUCE": "A pantry product often included in grocery multi-buy deals.",
    "SCENT": "A fragrance quality shoppers may compare in beauty products.",
    "SNACK": "A small food item commonly included in grocery promotions.",
    "STAMP": "A mark on a rewards card that tracks repeat purchases.",
    "SWIPE": "A motion used with some payment cards at checkout.",
    "SWEEP": "A prize drawing sometimes used to encourage shopper participation.",
    "TALLY": "A running count a shopper might keep while comparing costs.",
    "TILLS": "Checkout registers where store purchases are paid for.",
    "TOOLS": "Equipment for repairs and home-improvement projects.",
    "TOTES": "Reusable carry bags shoppers bring to a store.",
    "DROPS": "Hint: Reductions in price that shoppers love to spot.",
    "FINDS": "Hint: Interesting discoveries made while browsing deals.",
    "SWAPS": "Hint: Exchanges of one product for another.",
    "MARKS": "Hint: Symbols or labels used to identify items.",
    "DEPOT": "Hint: A storage or distribution center.",
    "POUCH": "Hint: A small flexible bag for carrying essentials.",
    "UNBOX": "Hint: Remove a new purchase from its packaging.",
    "SCOUT": "Hint: Search carefully for a worthwhile offer.",
    "STASH": "Hint: A supply kept aside for later.",
    "WAGON": "Hint: A four-wheeled carrier useful for hauling purchases.",
    "BROOM": "Hint: A long-handled tool for sweeping floors.",
    "SPICE": "Hint: An ingredient that adds flavor to food.",
    "BERRY": "Hint: A small juicy fruit often sold in cartons.",
    "LEMON": "Hint: A sour yellow citrus fruit.",
    "MELON": "Hint: A large sweet fruit with a rind.",
    "OLIVE": "Hint: A small fruit often used in salads.",
    "ONION": "Hint: A layered vegetable that can make you cry.",
    "BEANS": "Hint: Legumes sold dried or canned.",
    "PEACH": "Hint: A fuzzy-skinned summer fruit.",
    "GRAPE": "Hint: A small fruit often sold in bunches.",
    "LUNCH": "Hint: A midday meal.",
    "CANDY": "Hint: A sweet treat often handed out on Halloween.",
    "SWEET": "Hint: A taste associated with sugar.",
    "CREAM": "Hint: The rich dairy ingredient used in desserts.",
    "FROST": "Hint: A thin icy coating on a cold surface.",
    "SHEET": "Hint: A flat piece of fabric used on a bed.",
    "COUCH": "Hint: An upholstered seat for several people.",
    "TABLE": "Hint: Furniture with a flat top for dining or work.",
    "LIGHT": "Hint: Illumination from a lamp or bulb.",
    "CABLE": "Hint: A thick wire used to carry power or signals.",
    "BRUSH": "Hint: A tool with bristles for cleaning or grooming.",
    "APRON": "Hint: A protective garment worn while cooking.",
    "KNIFE": "Hint: A cutting utensil used in the kitchen.",
    "SPOON": "Hint: A utensil used to scoop or stir food.",
    "PLATE": "Hint: A flat dish used to serve food.",
    "BLEND": "Hint: Mix ingredients into a uniform combination.",
}

DAILY_CLUES = {
    "PRICE": "Today's word is the number you compare before paying for an item.",
    "SMART": "Today's word describes a shopper who plans before spending.",
    "SALES": "Today's word describes multiple store events where prices come down.",
    "SHARE": "Today's word is what you do when you pass a great deal to someone else.",
    "VALUE": "Today's word is what you receive compared with what you spend.",
    "STORE": "Today's word is where a shopper goes to buy something.",
    "DEALS": "Today's word means more than one savings opportunity.",
    "OFFER": "Today's word is a retailer's promotion or proposal.",
    "CASHY": "Today's word is a playful description of something connected to money.",
    "COINS": "Today's word is money you might keep in a jar, purse, or game reward.",
    "SAVER": "Today's word describes someone who looks for ways to spend less.",
    "SPEND": "Today's word is what happens when money leaves your wallet.",
    "STACK": "Today's word describes combining compatible discounts or rewards.",
    "TERMS": "Today's word means the conditions attached to an offer.",
    "LOCAL": "Today's word describes a deal from a nearby business.",
    "LOYAL": "Today's word describes a customer who keeps coming back.",
    "CARTS": "Today's word describes where online shoppers collect items before checkout.",
    "SHOPS": "Today's word means places where people buy things.",
    "CHECK": "Today's word is what you should do before paying or publishing a deal.",
    "BUYER": "Today's word means the person making a purchase.",
    "SAVED": "Today's word describes what happened when a discount reduced your cost.",
    "WATCH": "Today's word is what you do to keep an eye on a price.",
    "MATCH": "Today's word describes a retailer policy that may meet a competitor's price.",
    "CLICK": "Today's word is the action that opens a deal or retailer link.",
    "TODAY": "Today's word points to the day this puzzle was published.",
    "FLASH": "Today's word describes a short-lived promotion with limited time.",
    "BONUS": "Today's word means an extra reward added to the main savings.",
    "POINT": "Today's word is a unit in a loyalty or rewards program.",
    "ROUND": "Today's word means one cycle of guesses in a game.",
    "DRIVE": "Today's word can mean a trip to the store or motivation to save.",
    "FUNDS": "Today's word means money set aside for a purchase.", "GOODS": "Today's word means items offered for sale.",
    "PERKS": "Today's word means extra benefits attached to an offer.", "PROMO": "Today's word is a short name for a promotion.",
    "SCORE": "Today's word means points earned in a game or the value of a deal.", "SHELF": "Today's word is where a product waits in a store.",
    "TOTAL": "Today's word is the final amount after the shopping math is done.", "CENTS": "Today's word means the smaller units that make up a dollar.",
    "AISLE": "Today's word is the passage between store shelves.", "BULKS": "Today's word means large quantities grouped together.",
    "DELAY": "Today's word means a wait before something happens.", "LOWER": "Today's word is what a retailer may do to a price.",
    "PENNY": "Today's word means one cent.", "SAVES": "Today's word means reduces the amount someone must spend.",
    "TOKEN": "Today's word can represent a small unit of value or access.", "TREND": "Today's word means a pattern in prices, products, or shopping behavior.",
    "BAGEL": "Today's answer is a ring-shaped bakery item that can show up in a grocery special.",
    "BATCH": "Today's answer is a collection of offers reviewed together in one update.",
    "BREAD": "Today's answer is a familiar baked grocery staple that stores often promote.",
    "CHAIR": "Today's answer is a seat that shoppers may compare by style and price.",
    "CHIPS": "Today's answer is a crunchy packaged snack frequently sold in multi-buy offers.",
    "CRAFT": "Today's answer names a hobby area with supplies and kits to shop for.",
    "CRATE": "Today's answer is a box-like carrier useful for storing or transporting goods.",
    "DAIRY": "Today's answer is the grocery department that includes milk and yogurt.",
    "EARLY": "Today's answer describes access that begins before the public promotion window.",
    "FINAL": "Today's answer describes the amount remaining after eligible savings are applied.",
    "FLIER": "Today's answer is a store's printed or digital weekly advertisement.",
    "FRUIT": "Today's answer is fresh produce that may be featured in a weekly grocery ad.",
    "GLASS": "Today's answer is a transparent material used in drinkware and home goods.",
    "GRILL": "Today's answer is outdoor cooking equipment that may be discounted seasonally.",
    "JEWEL": "Today's answer can mean a precious stone or a jewelry-store item.",
    "JUMBO": "Today's answer marks a package or item size larger than the standard option.",
    "LINEN": "Today's answer is a home-textile category for items such as sheets.",
    "MEALS": "Today's answer is what shoppers plan and buy food to prepare.",
    "MILES": "Today's answer is a travel reward unit that can offset a later trip.",
    "MONTH": "Today's answer is a calendar unit often used to describe a recurring offer period.",
    "NOTES": "Today's answer can mean banknotes or written reminders for a shopping trip.",
    "PASTA": "Today's answer is a pantry staple often included in grocery promotions.",
    "PLANT": "Today's answer is a garden or indoor greenery purchase found in seasonal sales.",
    "PRINT": "Today's answer is what a shopper may do to make a paper coupon from an authorized offer.",
    "SAUCE": "Today's answer is a pantry food that can appear in a grocery multi-buy deal.",
    "SCENT": "Today's answer describes the fragrance of a beauty or home product.",
    "SNACK": "Today's answer is a small food item that retailers often group in promotions.",
    "STAMP": "Today's answer is a mark that can track progress on a store rewards card.",
    "SWIPE": "Today's answer is one way to use a payment card at checkout.",
    "SWEEP": "Today's answer is a prize drawing, not a discount or coupon.",
    "TALLY": "Today's answer is a running count that can help compare shopping costs.",
    "TILLS": "Today's answer is the plural name for checkout registers in a store.",
    "TOOLS": "Today's answer is equipment shoppers seek for repair and home-improvement jobs.",
    "TOTES": "Today's answer is reusable carry bags used for shopping.",
    "DROPS": "Today's answer: Reductions in price that shoppers love to spot.",
    "FINDS": "Today's answer: Interesting discoveries made while browsing deals.",
    "SWAPS": "Today's answer: Exchanges of one product for another.",
    "MARKS": "Today's answer: Symbols or labels used to identify items.",
    "DEPOT": "Today's answer: A storage or distribution center.",
    "POUCH": "Today's answer: A small flexible bag for carrying essentials.",
    "UNBOX": "Today's answer: Remove a new purchase from its packaging.",
    "SCOUT": "Today's answer: Search carefully for a worthwhile offer.",
    "STASH": "Today's answer: A supply kept aside for later.",
    "WAGON": "Today's answer: A four-wheeled carrier useful for hauling purchases.",
    "BROOM": "Today's answer: A long-handled tool for sweeping floors.",
    "SPICE": "Today's answer: An ingredient that adds flavor to food.",
    "BERRY": "Today's answer: A small juicy fruit often sold in cartons.",
    "LEMON": "Today's answer: A sour yellow citrus fruit.",
    "MELON": "Today's answer: A large sweet fruit with a rind.",
    "OLIVE": "Today's answer: A small fruit often used in salads.",
    "ONION": "Today's answer: A layered vegetable that can make you cry.",
    "BEANS": "Today's answer: Legumes sold dried or canned.",
    "PEACH": "Today's answer: A fuzzy-skinned summer fruit.",
    "GRAPE": "Today's answer: A small fruit often sold in bunches.",
    "LUNCH": "Today's answer: A midday meal.",
    "CANDY": "Today's answer: A sweet treat often handed out on Halloween.",
    "SWEET": "Today's answer: A taste associated with sugar.",
    "CREAM": "Today's answer: The rich dairy ingredient used in desserts.",
    "FROST": "Today's answer: A thin icy coating on a cold surface.",
    "SHEET": "Today's answer: A flat piece of fabric used on a bed.",
    "COUCH": "Today's answer: An upholstered seat for several people.",
    "TABLE": "Today's answer: Furniture with a flat top for dining or work.",
    "LIGHT": "Today's answer: Illumination from a lamp or bulb.",
    "CABLE": "Today's answer: A thick wire used to carry power or signals.",
    "BRUSH": "Today's answer: A tool with bristles for cleaning or grooming.",
    "APRON": "Today's answer: A protective garment worn while cooking.",
    "KNIFE": "Today's answer: A cutting utensil used in the kitchen.",
    "SPOON": "Today's answer: A utensil used to scoop or stir food.",
    "PLATE": "Today's answer: A flat dish used to serve food.",
    "BLEND": "Today's answer: Mix ingredients into a uniform combination.",
}

HINT_COSTS = (150, 300)
PUZZLES_PER_SESSION = 6
DAILY_BANK_LOW_WATER_MARK = PUZZLES_PER_SESSION * 14


def _hint_for_word(word):
    """Return a unique, non-answer-revealing hint instruction for a word."""
    return DAILY_HINTS.get(
        word,
        f"This is shopping vocabulary entry {DAILY_WORDS.index(word) + 1}; use the board feedback to place its letters.",
    )


def _clue_for_word(word):
    return DAILY_CLUES.get(
        word,
        f"Today's word is a five-letter term connected to shopping, deals, or checkout and begins with {word[0]}.",
    )


def ensure_daily_puzzle_schema(database):
    """Create the durable process list used to prevent puzzle reuse."""
    database.execute(
        ("""CREATE TABLE IF NOT EXISTS daily_puzzle_history (
            id BIGSERIAL PRIMARY KEY,
            puzzle_date TEXT NOT NULL,
            puzzle_index INTEGER NOT NULL,
            word TEXT NOT NULL UNIQUE,
            hint_instruction TEXT NOT NULL UNIQUE,
            clue TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(puzzle_date, puzzle_index)
        )""" if getattr(database, "is_postgres", False) else """CREATE TABLE IF NOT EXISTS daily_puzzle_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_date TEXT NOT NULL,
            puzzle_index INTEGER NOT NULL,
            word TEXT NOT NULL UNIQUE,
            hint_instruction TEXT NOT NULL UNIQUE,
            clue TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(puzzle_date, puzzle_index)
        )""")
    )
    database.commit()


def puzzle_date(day=None):
    return (day or date.today()).isoformat()


def _candidate_words_for(day):
    start = (day.toordinal() * 7) % len(DAILY_WORDS)
    return [DAILY_WORDS[(start + offset * 7) % len(DAILY_WORDS)] for offset in range(len(DAILY_WORDS))]


def _persistent_words_for(day, database):
    ensure_daily_puzzle_schema(database)
    day_text = puzzle_date(day)
    existing = database.execute(
        "SELECT word FROM daily_puzzle_history WHERE puzzle_date=? ORDER BY puzzle_index",
        (day_text,),
    ).fetchall()
    if len(existing) == PUZZLES_PER_SESSION:
        return tuple(row[0] for row in existing)
    if existing:
        database.execute("DELETE FROM daily_puzzle_history WHERE puzzle_date=?", (day_text,))

    used = database.execute("SELECT word, hint_instruction FROM daily_puzzle_history").fetchall()
    used_words = {row[0] for row in used}
    used_hints = {row[1] for row in used}
    selected = []
    for word in _candidate_words_for(day):
        hint = _hint_for_word(word)
        if word in used_words or hint in used_hints:
            continue
        selected.append((word, hint))
        used_words.add(word)
        used_hints.add(hint)
        if len(selected) == PUZZLES_PER_SESSION:
            break
    if len(selected) != PUZZLES_PER_SESSION:
        raise RuntimeError("Daily puzzle bank is exhausted; add unused words and hint instructions before continuing.")

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    database.executemany(
        """INSERT INTO daily_puzzle_history
           (puzzle_date, puzzle_index, word, hint_instruction, clue, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (day_text, index, word, hint, _clue_for_word(word), created_at)
            for index, (word, hint) in enumerate(selected)
        ],
    )
    database.commit()
    return tuple(word for word, _ in selected)


def daily_words_for(day=None, database=None):
    """Return the six-word set for a date, computed at request time.

    The running application therefore rolls to a new set after midnight
    without a code push, database write, or manual job. The date-derived
    rotation is deterministic so a session remains stable for every visitor
    on the same day.
    """
    day = day or date.today()
    if database is not None:
        return _persistent_words_for(day, database)
    return tuple(_candidate_words_for(day)[:PUZZLES_PER_SESSION])


def daily_bank_status(database):
    """Return capacity information for operators without exposing puzzle answers."""
    ensure_daily_puzzle_schema(database)
    used = database.execute("SELECT COUNT(*) FROM daily_puzzle_history").fetchone()[0]
    remaining = max(0, len(DAILY_WORDS) - used)
    return {
        "total_words": len(DAILY_WORDS),
        "used_words": used,
        "remaining_words": remaining,
        "days_remaining": remaining // PUZZLES_PER_SESSION,
        "needs_replenishment": remaining < DAILY_BANK_LOW_WATER_MARK,
    }


def answer_for(day=None, puzzle_index=0, database=None):
    day = day or date.today()
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    puzzle_index = max(0, min(PUZZLES_PER_SESSION - 1, puzzle_index))
    return daily_words_for(day, database=database)[puzzle_index]


def daily_clue(puzzle_index=0, day=None, database=None):
    answer = answer_for(day=day, puzzle_index=puzzle_index, database=database)
    return {"category": "Shopper's vocabulary", "clue": _clue_for_word(answer)}


def daily_session(day=None, database=None):
    return {
        "puzzle_count": PUZZLES_PER_SESSION,
        "clues": [daily_clue(index, day=day, database=database) for index in range(PUZZLES_PER_SESSION)],
    }


def editorial_puzzle_cards(day=None, database=None):
    """Return a spoiler-page view for a completed day, separate from gameplay."""
    selected_day = day or date.today()
    words = daily_words_for(selected_day, database=database)
    return [
        {
            "number": index + 1,
            "word": word,
            "clue": _clue_for_word(word),
            "hint": _hint_for_word(word),
        }
        for index, word in enumerate(words)
    ]


def daily_score(attempts=0, hints_used=0, won=False):
    """Return the visible game score; the contest backend can make this authoritative later."""
    try:
        attempts = max(0, int(attempts or 0))
        hints_used = max(0, min(len(HINT_COSTS), int(hints_used or 0)))
    except (TypeError, ValueError):
        attempts, hints_used = 0, 0
    if not won:
        return 0
    score = 1000 - max(0, attempts - 1) * 100 - sum(HINT_COSTS[:hints_used])
    return max(0, score)


def score_guess(guess, answer):
    """Score a five-letter guess with duplicate-letter-safe feedback."""
    result = ["absent"] * len(answer)
    remaining = {}
    for index, letter in enumerate(answer):
        if guess[index] == letter:
            result[index] = "correct"
        else:
            remaining[letter] = remaining.get(letter, 0) + 1
    for index, letter in enumerate(guess):
        if result[index] == "correct":
            continue
        if remaining.get(letter, 0):
            result[index] = "present"
            remaining[letter] -= 1
    return result


def evaluate_guess(guess, attempts=0, puzzle_index=0, hints_used=0, database=None):
    normalized = re.sub(r"[^a-z]", "", (guess or "").lower()).upper()
    if len(normalized) != 5 or not normalized.isalpha():
        return {"ok": False, "error": "Enter a five-letter word."}
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    if puzzle_index < 0 or puzzle_index >= PUZZLES_PER_SESSION:
        return {"ok": False, "error": "That puzzle is not available in this session."}
    answer = answer_for(puzzle_index=puzzle_index, database=database)
    pattern = score_guess(normalized, answer)
    won = normalized == answer
    try:
        attempts = int(attempts or 0)
    except (TypeError, ValueError):
        attempts = 0
    reveal = won or attempts >= 6
    return {
        "ok": True,
        "guess": normalized,
        "pattern": pattern,
        "won": won,
        "finished": reveal,
        "puzzle_date": puzzle_date(),
        "puzzle_index": puzzle_index,
        "next_puzzle_index": puzzle_index + 1 if reveal and puzzle_index + 1 < PUZZLES_PER_SESSION else None,
        "session_complete": reveal and puzzle_index == PUZZLES_PER_SESSION - 1,
        "points": daily_score(attempts, hints_used, won) if reveal else None,
        "answer": answer if reveal else None,
    }


def daily_hint(hint_index=0, puzzle_index=0, database=None):
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    if puzzle_index < 0 or puzzle_index >= PUZZLES_PER_SESSION:
        return {"ok": False, "error": "That puzzle is not available in this session."}
    answer = answer_for(puzzle_index=puzzle_index, database=database)
    if hint_index == 0:
        return {"ok": True, "hint_index": 0, "hint": _hint_for_word(answer), "cost": HINT_COSTS[0]}
    if hint_index == 1:
        return {"ok": True, "hint_index": 1, "hint": f"The word starts with {answer[0]}.", "letter": answer[0], "cost": HINT_COSTS[1]}
    return {"ok": False, "error": "No more hints remain for today's puzzle."}
