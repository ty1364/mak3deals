import unittest
import sqlite3
from datetime import date, timedelta

from daily_game import PUZZLES_PER_SESSION, answer_for, daily_words_for, ensure_daily_puzzle_schema


class DailyGameRotationTests(unittest.TestCase):
    def setUp(self):
        self.database = sqlite3.connect(":memory:")
        ensure_daily_puzzle_schema(self.database)

    def tearDown(self):
        self.database.close()

    def test_each_date_has_six_unique_puzzles(self):
        words = daily_words_for(date(2026, 9, 30))
        self.assertEqual(len(words), PUZZLES_PER_SESSION)
        self.assertEqual(len(set(words)), PUZZLES_PER_SESSION)

    def test_next_day_changes_every_puzzle_position(self):
        yesterday = date(2026, 9, 29)
        today = yesterday + timedelta(days=1)
        self.assertTrue(all(answer_for(yesterday, i) != answer_for(today, i) for i in range(PUZZLES_PER_SESSION)))

    def test_rotation_is_stable_for_same_date(self):
        target = date(2026, 10, 1)
        self.assertEqual(daily_words_for(target), daily_words_for(target))

    def test_process_list_persists_one_set_for_the_day(self):
        target = date(2026, 10, 2)
        first = daily_words_for(target, database=self.database)
        second = daily_words_for(target, database=self.database)
        self.assertEqual(first, second)
        rows = self.database.execute(
            "SELECT word, hint_instruction FROM daily_puzzle_history WHERE puzzle_date=?",
            (target.isoformat(),),
        ).fetchall()
        self.assertEqual(len(rows), PUZZLES_PER_SESSION)
        self.assertEqual(len({row[0] for row in rows}), PUZZLES_PER_SESSION)
        self.assertEqual(len({row[1] for row in rows}), PUZZLES_PER_SESSION)

    def test_process_list_never_reuses_words_or_hint_instructions(self):
        for offset in range(5):
            daily_words_for(date(2026, 10, 3) + timedelta(days=offset), database=self.database)
        rows = self.database.execute(
            "SELECT word, hint_instruction FROM daily_puzzle_history"
        ).fetchall()
        self.assertEqual(len(rows), len({row[0] for row in rows}))
        self.assertEqual(len(rows), len({row[1] for row in rows}))


if __name__ == "__main__":
    unittest.main()
