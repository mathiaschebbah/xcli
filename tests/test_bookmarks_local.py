"""Tests de la recherche locale dans les signets (`xa bookmarks --grep`).

Logique PURE (matcher + grep + cache), sans réseau ni cookies. Lancer avec :

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from xa.core import bookmarks_local as bm

ROWS = [
    {"id": "1", "author": "emilkowalski",
     "text": "I made a motion vocabulary: stagger, crossfade, layout animation"},
    {"id": "2", "author": "mattpocockuk",
     "text": "Preview of an AI Coding Dictionary I'm shipping"},
    {"id": "3", "author": "someone",
     "text": "A tweet about spacing and typography in design"},
    {"id": "4", "author": "noise", "text": "totally unrelated content"},
]


class TestMatcher(unittest.TestCase):
    def _ids(self, rows):
        return [r["id"] for r in rows]

    def test_or_is_default(self):
        # OR : au moins un terme présent.
        m = bm.build_matcher("vocabulary dictionary")
        self.assertEqual(self._ids(bm.grep(ROWS, m)), ["1", "2"])

    def test_and_mode(self):
        # AND : tous les termes (ici aucun row n'a les deux).
        m = bm.build_matcher("vocabulary dictionary", require_all=True)
        self.assertEqual(bm.grep(ROWS, m), [])
        # AND qui matche bien.
        m2 = bm.build_matcher("motion stagger", require_all=True)
        self.assertEqual(self._ids(bm.grep(ROWS, m2)), ["1"])

    def test_case_insensitive(self):
        m = bm.build_matcher("DICTIONARY")
        self.assertEqual(self._ids(bm.grep(ROWS, m)), ["2"])

    def test_searches_author_field(self):
        # Le grep cherche aussi dans l'auteur, pas que le texte.
        m = bm.build_matcher("mattpocockuk")
        self.assertEqual(self._ids(bm.grep(ROWS, m)), ["2"])

    def test_regex_mode(self):
        m = bm.build_matcher(r"vocab\w*|dictionary", regex=True)
        self.assertEqual(self._ids(bm.grep(ROWS, m)), ["1", "2"])

    def test_empty_pattern_matches_all(self):
        # Pattern vide = pas de filtre (évite un grep no-op silencieux à 0).
        m = bm.build_matcher("   ")
        self.assertEqual(len(bm.grep(ROWS, m)), len(ROWS))

    def test_handles_missing_fields(self):
        m = bm.build_matcher("anything")
        # row sans 'text' ni 'author' ne crashe pas.
        self.assertEqual(bm.grep([{"id": "x"}], m), [])


class TestCache(unittest.TestCase):
    def test_roundtrip_and_complete_flag(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            bm.save_cache(ROWS, fetched_at=time.time(), complete=True, path=p)
            blob = bm.load_cache(path=p)
            self.assertIsNotNone(blob)
            self.assertTrue(blob["complete"])
            self.assertEqual(len(blob["rows"]), len(ROWS))

    def test_ttl_expiry(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            bm.save_cache(ROWS, fetched_at=time.time() - 10_000, path=p)
            # Avec un TTL court, le cache vieux est considéré périmé.
            self.assertIsNone(bm.load_cache(ttl=600, path=p))
            # Avec un TTL large, il est encore valide.
            self.assertIsNotNone(bm.load_cache(ttl=100_000, path=p))

    def test_missing_file(self):
        with TemporaryDirectory() as d:
            self.assertIsNone(bm.load_cache(path=Path(d) / "nope.json"))

    def test_corrupt_file(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text("{ not json")
            self.assertIsNone(bm.load_cache(path=p))

    def test_complete_defaults_false_for_legacy_blob(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            # Ancien format sans 'complete'.
            p.write_text('{"fetched_at": %f, "rows": []}' % time.time())
            blob = bm.load_cache(path=p)
            self.assertIsNotNone(blob)
            self.assertFalse(blob["complete"])


if __name__ == "__main__":
    unittest.main()
