"""Core implementation of the Count Min Sketch.

The Count Min Sketch is a probabilistic data structure that estimates the
frequency of items in a data stream using sub-linear space. It uses a matrix
of counters and multiple pairwise-independent hash functions. An update
increments one counter per row; a query returns the minimum of the counters
selected by the hash functions.

The trade-off is deliberate: the sketch may overestimate frequencies, but it
never underestimates them. The error is bounded with high probability when
the width and depth are chosen appropriately.

We avoid third-party dependencies and implement hash functions from the
standard library's hashlib module so the library works in restricted
environments.
"""

from __future__ import annotations

import hashlib
import math
from array import array
from typing import Iterable, Sequence


class CountMinSketch:
    """A fixed-size Count Min Sketch for approximate frequency counts.

    The sketch is created with a chosen width, depth, and an optional seed.
    The seed makes the hash functions deterministic and reproducible, which is
    essential for testing and for consistent behaviour across processes.

    Attributes:
        width: Number of columns in the counter matrix.
        depth: Number of rows in the counter matrix.
        seed: Seed used to derive hash salts.
    """

    def __init__(self, width: int, depth: int, seed: int = 0) -> None:
        """Create a Count Min Sketch.

        Args:
            width: Number of columns per row. Must be at least 1.
            depth: Number of rows. Must be at least 1.
            seed: Integer seed for hash derivation. Defaults to 0.

        Raises:
            ValueError: If width or depth is less than 1, or if seed is
                negative.
        """
        if width < 1:
            raise ValueError("width must be at least 1")
        if depth < 1:
            raise ValueError("depth must be at least 1")
        if seed < 0:
            raise ValueError("seed must be non-negative")

        self.width = width
        self.depth = depth
        self.seed = seed

        # 'I' is an unsigned int (usually 4 bytes). It is sufficient for
        # frequency counts and keeps the memory footprint predictable.
        self._table = [array("I", [0]) * width for _ in range(depth)]

        # Precompute salts so the same item hashes differently in each row.
        # Salts are 64-bit values derived from the seed and row index. The
        # derivation is deterministic and does not require random numbers.
        self._salts = tuple(
            self._derive_salt(row) for row in range(depth)
        )

    def _derive_salt(self, row: int) -> int:
        """Return a 64-bit salt for the given row index.

        The salt is computed from the seed and row using SHA-256. This gives
        good bit mixing without relying on a particular platform's random
        number generator. The result is masked to 64 bits so the hash inputs
        have a consistent size.
        """
        data = f"{self.seed}:{row}".encode("utf-8")
        digest = hashlib.sha256(data).digest()
        return int.from_bytes(digest[:8], "big")

    def _hash(self, item: str, salt: int) -> int:
        """Hash an item and salt to a column index in [0, width).

        We use SHA-256 to produce a 64-bit integer, then reduce it modulo
        width. SHA-256 is in the standard library and gives a high-quality
        hash. The reduction is biased if width does not divide 2^64, but this
        bias is negligible for realistic widths and does not affect the
        sketch's guarantees in practice.
        """
        data = item.encode("utf-8")
        # Combine item bytes and salt bytes in a way that cannot be ambiguous.
        # We prepend the salt length so different salts cannot produce the
        # same concatenation.
        salt_bytes = salt.to_bytes(8, "big")
        hasher = hashlib.sha256()
        hasher.update(salt_bytes)
        hasher.update(len(data).to_bytes(8, "big"))
        hasher.update(data)
        digest = hasher.digest()
        value = int.from_bytes(digest[:8], "big")
        return value % self.width

    def update(self, item: str, count: int = 1) -> None:
        """Increment the frequency estimate for an item.

        Args:
            item: The item whose frequency is being updated.
            count: Number of occurrences to add. Must be non-negative.

        Raises:
            ValueError: If count is negative.
        """
        if count < 0:
            raise ValueError("count must be non-negative")
        if count == 0:
            return

        for row in range(self.depth):
            col = self._hash(item, self._salts[row])
            # Overflow handling: 'I' is unsigned, so addition wraps around.
            # This is acceptable for a sketch; the estimate will still be a
            # lower bound up to the point of overflow. We do not raise because
            # the sketch is designed for approximate counts and large counts
            # are expected to be rare.
            self._table[row][col] += count

    def estimate(self, item: str) -> int:
        """Return the estimated frequency for an item.

        The estimate is the minimum of the counters selected by the hash
        functions. This value is always at least the true frequency, and
        usually close to it when the sketch is sized appropriately.

        Args:
            item: The item whose frequency is being queried.

        Returns:
            An integer estimate. It is never negative.
        """
        min_count = None
        for row in range(self.depth):
            col = self._hash(item, self._salts[row])
            value = self._table[row][col]
            if min_count is None or value < min_count:
                min_count = value
        return int(min_count if min_count is not None else 0)

    def merge(self, other: "CountMinSketch") -> None:
        """Merge another sketch into this one.

        The two sketches must have the same width, depth, and seed. Merging
        adds the corresponding counters. This is useful for distributed
        counting where each worker maintains its own sketch and the results
        are combined later.

        Args:
            other: Another CountMinSketch with identical parameters.

        Raises:
            TypeError: If other is not a CountMinSketch.
            ValueError: If width, depth, or seed differ.
        """
        if not isinstance(other, CountMinSketch):
            raise TypeError("other must be a CountMinSketch")
        if (
            self.width != other.width
            or self.depth != other.depth
            or self.seed != other.seed
        ):
            raise ValueError(
                "cannot merge sketches with different width, depth, or seed"
            )

        for row in range(self.depth):
            for col in range(self.width):
                self._table[row][col] += other._table[row][col]
