# Count Min Sketch

A small, dependency-free Python library that estimates item frequencies in a data stream using the Count Min Sketch algorithm.

```python
from count_min_sketch import CountMinSketch

sketch = CountMinSketch(width=1000, depth=7, seed=42)
sketch.update("apple")
sketch.update("apple", count=3)
print(sketch.estimate("apple"))  # prints 4 (or slightly more if collisions occur)
```

## Why this exists

Counting exact frequencies in an unbounded stream requires space proportional to the number of distinct items. Count Min Sketch trades exactness for a fixed, sub-linear memory footprint: it stores a matrix of counters and updates only a few counters per item. Queries return a value that is always at least the true frequency, and usually close to it. The error is one-sided (never an underestimate) and can be controlled by choosing the sketch's width and depth.

The implementation uses only the Python standard library. Hash functions are derived with SHA-256 from a user-supplied seed, so results are deterministic and reproducible across runs.

## Awkward edge

Counter values are stored as unsigned 32-bit integers. If a counter exceeds 2^32 - 1, it wraps around. This is accepted behaviour for a sketch, but if your workload routinely produces counts that large, you should increase the sketch width to reduce per-counter load or consider a different structure.

## API

### `CountMinSketch(width, depth, seed=0)`

Creates a sketch with `width` columns and `depth` rows. `width` and `depth` must be at least 1; `seed` must be non-negative.

### `update(item, count=1)`

Adds `count` occurrences of `item`. `count` must be non-negative.

### `estimate(item)`

Returns the estimated frequency for `item`. The returned value is an integer and is never less than the true frequency seen so far.

### `merge(other)`

Adds all counters from `other` into this sketch. Both sketches must have the same `width`, `depth`, and `seed`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

