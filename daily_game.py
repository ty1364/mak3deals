"""Server-side daily word puzzle for Mak3Deals."""

from datetime import date
import re


DAILY_WORDS = [
    "PRICE", "SMART", "SALES", "SHARE", "VALUE", "STORE", "DEALS", "OFFER",
    "CASHY", "COINS", "SAVER", "SPEND", "STACK", "TERMS", "LOCAL", "LOYAL",
    "CARTS", "SHOPS", "CHECK", "BUYER", "SAVED", "WATCH", "MATCH", "CLICK",
    "TODAY", "FLASH", "BONUS", "POINT", "ROUND", "DRIVE",
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
}


def puzzle_date():
    return date.today().isoformat()


def answer_for(day=None):
    day = day or date.today()
    return DAILY_WORDS[(day.toordinal() * 7) % len(DAILY_WORDS)]


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


def evaluate_guess(guess, attempts=0):
    normalized = re.sub(r"[^a-z]", "", (guess or "").lower()).upper()
    if len(normalized) != 5 or not normalized.isalpha():
        return {"ok": False, "error": "Enter a five-letter word."}
    answer = answer_for()
    pattern = score_guess(normalized, answer)
    won = normalized == answer
    reveal = won or int(attempts or 0) >= 6
    return {
        "ok": True,
        "guess": normalized,
        "pattern": pattern,
        "won": won,
        "finished": won,
        "puzzle_date": puzzle_date(),
        "answer": answer if reveal else None,
    }


def daily_hint(hint_index=0):
    answer = answer_for()
    if hint_index == 0:
        return {"ok": True, "hint_index": 0, "hint": DAILY_HINTS.get(answer, "This word is connected to finding a better deal.")}
    if hint_index == 1:
        return {"ok": True, "hint_index": 1, "hint": f"The word starts with {answer[0]}.", "letter": answer[0]}
    return {"ok": False, "error": "No more hints remain for today's puzzle."}
