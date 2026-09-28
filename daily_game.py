"""Server-side daily word puzzle for Mak3Deals."""

from datetime import date
import re


DAILY_WORDS = [
    "PRICE", "SMART", "SALES", "SHARE", "VALUE", "STORE", "DEALS", "OFFER",
    "CASHY", "COINS", "SAVER", "SPEND", "STACK", "TERMS", "LOCAL", "LOYAL",
    "CARTS", "SHOPS", "CHECK", "BUYER", "SAVED", "WATCH", "MATCH", "CLICK",
    "TODAY", "FLASH", "BONUS", "POINT", "ROUND", "DRIVE",
]


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
