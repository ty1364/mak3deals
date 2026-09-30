import unittest
from datetime import date, timedelta

from daily_game import PUZZLES_PER_SESSION, answer_for, daily_words_for


class DailyGameRotationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
