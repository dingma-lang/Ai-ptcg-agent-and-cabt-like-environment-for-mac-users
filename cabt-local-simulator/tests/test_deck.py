from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cabt_local.card_catalog import CardCatalog, CardRecord
from cabt_local.deck import DeckError, convert_ptcglive_text, deck_report, load_deck, validate_deck, write_deck


class DeckTests(unittest.TestCase):
    def test_loads_exactly_60_numeric_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.csv"
            write_deck(range(1, 61), path)
            ids = load_deck(path)
        self.assertEqual(len(ids), 60)
        self.assertEqual(ids[0], 1)
        self.assertEqual(ids[-1], 60)

    def test_rejects_59_or_61_cards(self) -> None:
        self.assertIn("59", validate_deck(range(59))[0])
        self.assertIn("61", validate_deck(range(1, 62))[0])

    def test_invalid_non_numeric_line_reports_file_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("1\nnot-a-card\n", encoding="utf-8")
            with self.assertRaises(DeckError):
                load_deck(path)

    def test_unsupported_ids_are_reported_against_catalog(self) -> None:
        catalog = CardCatalog([CardRecord(1, "One"), CardRecord(2, "Two")], source="fixture")
        errors = validate_deck([1] * 59 + [99], catalog)
        self.assertTrue(any("99" in error for error in errors))

    def test_separate_deck_a_and_deck_b_loading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.csv"
            b = Path(tmp) / "b.csv"
            write_deck([1] * 60, a)
            write_deck([2] * 60, b)
            self.assertEqual(load_deck(a), [1] * 60)
            self.assertEqual(load_deck(b), [2] * 60)

    def test_deck_report_has_counts_and_names(self) -> None:
        catalog = CardCatalog([CardRecord(1, "One"), CardRecord(2, "Two")], source="fixture")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.csv"
            write_deck([1] * 30 + [2] * 30, path)
            report = deck_report(path, catalog)
        self.assertTrue(report.valid_size)
        self.assertEqual(report.rows[0]["count"], 30)
        self.assertEqual(report.rows[0]["name"], "One")

    def test_ptcglive_converter_requires_exact_unique_match(self) -> None:
        catalog = CardCatalog(
            [
                CardRecord(10, "Finizen", set_name="TWM", collector_number="59"),
                CardRecord(11, "Finizen", set_name="TWM", collector_number="60"),
            ],
            source="fixture",
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "deck.txt"
            out = Path(tmp) / "deck.csv"
            src.write_text("4 Finizen TWM 59\n1 Missing SET 1\n", encoding="utf-8")
            report = convert_ptcglive_text(src, out, catalog)
        self.assertEqual(report.converted_count, 4)
        self.assertEqual(len(report.issues), 1)


if __name__ == "__main__":
    unittest.main()

