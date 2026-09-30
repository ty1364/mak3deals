"""Server-side daily word puzzle for Mak3Deals."""

from datetime import date
import re


DAILY_WORDS = [
    "PRICE", "SMART", "SALES", "SHARE", "VALUE", "STORE", "DEALS", "OFFER",
    "CASHY", "COINS", "SAVER", "SPEND", "STACK", "TERMS", "LOCAL", "LOYAL",
    "CARTS", "SHOPS", "CHECK", "BUYER", "SAVED", "WATCH", "MATCH", "CLICK",
    "TODAY", "FLASH", "BONUS", "POINT", "ROUND", "DRIVE",
    "FUNDS", "GOODS", "PERKS", "PROMO", "SCORE", "SHELF", "TOTAL", "CENTS",
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
}

HINT_COSTS = (150, 300)
PUZZLES_PER_SESSION = 6


def puzzle_date():
    return date.today().isoformat()


def daily_words_for(day=None):
    """Return the six-word set for a date, computed at request time.

    The running application therefore rolls to a new set after midnight
    without a code push, database write, or manual job. The date-derived
    rotation is deterministic so a session remains stable for every visitor
    on the same day.
    """
    day = day or date.today()
    start = (day.toordinal() * 7) % len(DAILY_WORDS)
    return tuple(DAILY_WORDS[(start + index * 7) % len(DAILY_WORDS)] for index in range(PUZZLES_PER_SESSION))


def answer_for(day=None, puzzle_index=0):
    day = day or date.today()
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    puzzle_index = max(0, min(PUZZLES_PER_SESSION - 1, puzzle_index))
    return daily_words_for(day)[puzzle_index]


def daily_clue(puzzle_index=0):
    answer = answer_for(puzzle_index=puzzle_index)
    return {"category": "Shopper's vocabulary", "clue": DAILY_CLUES.get(answer, "Today's word is connected to finding a better deal.")}


def daily_session():
    return {
        "puzzle_count": PUZZLES_PER_SESSION,
        "clues": [daily_clue(index) for index in range(PUZZLES_PER_SESSION)],
    }


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


def evaluate_guess(guess, attempts=0, puzzle_index=0, hints_used=0):
    normalized = re.sub(r"[^a-z]", "", (guess or "").lower()).upper()
    if len(normalized) != 5 or not normalized.isalpha():
        return {"ok": False, "error": "Enter a five-letter word."}
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    if puzzle_index < 0 or puzzle_index >= PUZZLES_PER_SESSION:
        return {"ok": False, "error": "That puzzle is not available in this session."}
    answer = answer_for(puzzle_index=puzzle_index)
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


def daily_hint(hint_index=0, puzzle_index=0):
    try:
        puzzle_index = int(puzzle_index)
    except (TypeError, ValueError):
        puzzle_index = 0
    if puzzle_index < 0 or puzzle_index >= PUZZLES_PER_SESSION:
        return {"ok": False, "error": "That puzzle is not available in this session."}
    answer = answer_for(puzzle_index=puzzle_index)
    if hint_index == 0:
        return {"ok": True, "hint_index": 0, "hint": DAILY_HINTS.get(answer, "This word is connected to finding a better deal."), "cost": HINT_COSTS[0]}
    if hint_index == 1:
        return {"ok": True, "hint_index": 1, "hint": f"The word starts with {answer[0]}.", "letter": answer[0], "cost": HINT_COSTS[1]}
    return {"ok": False, "error": "No more hints remain for today's puzzle."}
