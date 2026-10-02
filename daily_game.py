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
