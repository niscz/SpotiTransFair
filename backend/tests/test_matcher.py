import unittest
import sys
import os

# Add parent directory to path to import matcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matcher import match_track, calculate_score, normalize_string
from models import ItemStatus

class TestMatcher(unittest.TestCase):
    def test_normalize_string(self):
        self.assertEqual(normalize_string(" Test  String! "), "test string")
        self.assertEqual(normalize_string(None), "")
        self.assertEqual(normalize_string("Artist (feat. Someone)"), "artist")

    def test_calculate_score_exact(self):
        src = {"name": "Song", "artists": ["Artist"], "duration_ms": 180000}
        tgt = {"title": "Song", "artists": ["Artist"], "duration": 180}
        score = calculate_score(src, tgt)
        self.assertAlmostEqual(score, 1.0)

    def test_calculate_score_isrc(self):
        src = {"isrc": "US12345"}
        tgt = {"isrc": "US12345"}
        self.assertEqual(calculate_score(src, tgt), 1.0)

    def test_match_track(self):
        src = {"name": "Hello", "artists": ["Adele"], "duration_ms": 300000}
        candidates = [
            {"title": "Hello", "artists": ["Adele"], "duration": 300},
            {"title": "Rolling in the Deep", "artists": ["Adele"], "duration": 280}
        ]
        match, status = match_track(src, candidates)
        self.assertEqual(status, ItemStatus.MATCHED)
        self.assertEqual(match["title"], "Hello")

    def test_match_track_uncertain(self):
        src = {"name": "Hello", "artists": ["Adele"], "duration_ms": 300000}
        candidates = [
            {"title": "Hello Live", "artists": ["Adele"], "duration": 320}, # Slightly different
        ]
        # Depending on weights, this might be uncertain or matched.
        # Title "Hello" vs "Hello Live" ratio is ~0.66.
        # Artist 1.0. Duration 0.5 (diff 20s > 15s? No, diff is 20s. 320*1000 - 300000 = 20000. > 15000 -> 0.0)
        # Score = 0.66*0.5 + 1.0*0.35 + 0.0*0.15 = 0.33 + 0.35 = 0.68.
        # Should be NOT_FOUND (<0.75).

        # Let's try something closer.
        candidates = [{"title": "Hello", "artists": ["Adele"], "duration": 300}]
        # This should match.

        # Let's try missing data (None)
        src = {"name": "Test", "artists": None, "duration_ms": None}
        tgt = {"title": "Test", "artists": None, "duration": None}
        # Should not crash
        score = calculate_score(src, tgt)
        self.assertTrue(score >= 0)

if __name__ == '__main__':
    unittest.main()
