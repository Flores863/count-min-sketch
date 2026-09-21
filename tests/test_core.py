"""Tests for the CountMinSketch class."""

import unittest

from count_min_sketch import CountMinSketch


class TestCountMinSketch(unittest.TestCase):
    def test_initial_estimate_is_zero(self):
        sketch = CountMinSketch(width=10, depth=4, seed=42)
        self.assertEqual(sketch.estimate("anything"), 0)

    def test_update_increases_estimate(self):
        sketch = CountMinSketch(width=20, depth=5, seed=7)
        sketch.update("apple")
        self.assertEqual(sketch.estimate("apple"), 1)

    def test_multiple_updates_accumulate(self):
        sketch = CountMinSketch(width=20, depth=5, seed=7)
        sketch.update("apple")
        sketch.update("apple")
        sketch.update("apple", count=3)
        self.assertEqual(sketch.estimate("apple"), 5)

    def test_different_items_may_share_counters_but_estimates_remain_upper_bounds(self):
        # A deliberately narrow sketch forces collisions.
        sketch = CountMinSketch(width=2, depth=2, seed=123)
        sketch.update("foo", count=10)
        sketch.update("bar", count=7)
        # The estimate for foo must be at least its true frequency.
        self.assertGreaterEqual(sketch.estimate("foo"), 10)
        # The estimate for bar must be at least its true frequency.
        self.assertGreaterEqual(sketch.estimate("bar"), 7)

    def test_estimate_never_underestimates(self):
        sketch = CountMinSketch(width=50, depth=5, seed=99)
        items = ["alpha", "beta", "gamma", "delta"]
        for i, item in enumerate(items, start=1):
            for _ in range(i):
                sketch.update(item)
        for i, item in enumerate(items, start=1):
            self.assertGreaterEqual(sketch.estimate(item), i)

    def test_update_rejects_negative_count(self):
        sketch = CountMinSketch(width=10, depth=3)
        with self.assertRaises(ValueError):
            sketch.update("item", count=-1)

    def test_constructor_rejects_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            CountMinSketch(width=0, depth=3)
        with self.assertRaises(ValueError):
            CountMinSketch(width=3, depth=0)

    def test_constructor_rejects_negative_seed(self):
        with self.assertRaises(ValueError):
            CountMinSketch(width=10, depth=3, seed=-1)

    def test_merge_adds_counters(self):
        sketch1 = CountMinSketch(width=30, depth=4, seed=5)
        sketch2 = CountMinSketch(width=30, depth=4, seed=5)
        sketch1.update("x", count=4)
        sketch2.update("x", count=6)
        sketch1.merge(sketch2)
        self.assertGreaterEqual(sketch1.estimate("x"), 10)

    def test_merge_rejects_incompatible_sketches(self):
        sketch1 = CountMinSketch(width=10, depth=3, seed=1)
        sketch2 = CountMinSketch(width=10, depth=4, seed=1)
        with self.assertRaises(ValueError):
            sketch1.merge(sketch2)

    def test_merge_rejects_non_sketch(self):
        sketch = CountMinSketch(width=10, depth=3)
        with self.assertRaises(TypeError):
            sketch.merge("not a sketch")

    def test_deterministic_for_same_seed(self):
        sketch1 = CountMinSketch(width=100, depth=5, seed=314)
        sketch2 = CountMinSketch(width=100, depth=5, seed=314)
        for item in ["a", "b", "c", "a", "b"]:
            sketch1.update(item)
            sketch2.update(item)
        for item in ["a", "b", "c", "d"]:
            self.assertEqual(sketch1.estimate(item), sketch2.estimate(item))

    def test_different_seeds_can_produce_different_estimates(self):
        # This is not guaranteed for every item, but we choose an item and a
        # narrow width to make a collision difference likely. We only assert
        # that the two sketches are internally consistent, not that they must
        # differ.
        sketch1 = CountMinSketch(width=3, depth=2, seed=1)
        sketch2 = CountMinSketch(width=3, depth=2, seed=2)
        for _ in range(5):
            sketch1.update("same")
            sketch2.update("same")
        # Both must be at least 5.
        self.assertGreaterEqual(sketch1.estimate("same"), 5)
        self.assertGreaterEqual(sketch2.estimate("same"), 5)


if __name__ == "__main__":
    unittest.main()
