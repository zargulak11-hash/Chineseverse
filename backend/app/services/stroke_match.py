"""Server-side check of a traced character, using the same stroke data the
browser's HanziWriter quiz uses (Hanzi.stroke_data: makemeahanzi `strokes`
+ `medians`, in its 1024-unit character space).

POST /api/hanzi/{id}/write used to take {"total_mistakes": 0} and nothing
else, so any request added writing mastery. The browser now sends the points
of every stroke it drew (HanziWriter's drawnPath.points, already in character
space) and this module re-runs HanziWriter's own stroke matcher on them --
a straight port of strokeMatches()/getMatchData() from hanzi-writer 3.7
(frontend/node_modules/hanzi-writer/dist/hanzi-writer.js), with the same
thresholds -- so a stroke only counts if its geometry really matches the
expected stroke of this character, in stroke order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# hanzi-writer's constants
COSINE_SIMILARITY_THRESHOLD = 0.0
START_AND_END_DIST_THRESHOLD = 250.0
FRECHET_THRESHOLD = 0.4
MIN_LEN_THRESHOLD = 0.35
AVERAGE_DISTANCE_THRESHOLD = 350.0
SHAPE_FIT_ROTATIONS = [math.pi / 16, math.pi / 32, 0.0, -math.pi / 32, -math.pi / 16]

# HanziWriter's own leniency (the quiz uses the default). The browser
# matches unrounded pointer positions while drawnPath.points are rounded to
# 0.1 units, so a stroke that fails at exactly 1.0 gets one retry at
# ROUNDING_LENIENCY -- a 2% margin (a few units in a 1024-unit box), far
# below what any wrong stroke is off by. Not a single higher leniency:
# leniency also lets *later* strokes "fit better", so it is not monotonic.
SERVER_LENIENCY = 1.0
ROUNDING_LENIENCY = 1.02

Point = tuple[float, float]


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _length(points: list[Point]) -> float:
    return sum(_dist(points[i], points[i - 1]) for i in range(1, len(points)))


def _cosine(a: Point, b: Point) -> float:
    ma, mb = math.hypot(*a), math.hypot(*b)
    if ma == 0 or mb == 0:
        return float("nan")  # JS divides by zero here too; NaN never passes a ">" test
    return (a[0] * b[0] + a[1] * b[1]) / ma / mb


def _vectors(points: list[Point]) -> list[Point]:
    return [(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(1, len(points))]


def _extend(p1: Point, p2: Point, d: float) -> Point:
    vx, vy = p2[0] - p1[0], p2[1] - p1[1]
    norm = d / math.hypot(vx, vy)
    return (p2[0] + norm * vx, p2[1] + norm * vy)


def _frechet(c1: list[Point], c2: list[Point]) -> float:
    long_c, short_c = (c1, c2) if len(c1) >= len(c2) else (c2, c1)
    prev: list[float] = []
    for i in range(len(long_c)):
        cur: list[float] = []
        for j in range(len(short_c)):
            d = _dist(long_c[i], short_c[j])
            if i == 0 and j == 0:
                v = d
            elif i > 0 and j == 0:
                v = max(prev[0], d)
            elif i == 0:
                v = max(cur[-1], d)
            else:
                v = max(min(prev[j], prev[j - 1], cur[-1]), d)
            cur.append(v)
        prev = cur
    return prev[len(short_c) - 1]


def _subdivide(curve: list[Point], max_len: float = 0.05) -> list[Point]:
    out = curve[:1]
    for p in curve[1:]:
        prev = out[-1]
        seg = _dist(p, prev)
        if seg > max_len:
            n = math.ceil(seg / max_len)
            step = seg / n
            for i in range(n):
                out.append(_extend(p, prev, -1 * step * (i + 1)))
        else:
            out.append(p)
    return out


def _outline(curve: list[Point], num_points: int = 30) -> list[Point]:
    seg_len = _length(curve) / (num_points - 1)
    out = [curve[0]]
    remaining = list(curve[1:])
    for _ in range(num_points - 2):
        last = out[-1]
        left = seg_len
        while True:
            nd = _dist(last, remaining[0])
            if nd < left and len(remaining) > 1:
                left -= nd
                last = remaining.pop(0)
            else:
                out.append(_extend(last, remaining[0], left - nd))
                break
    out.append(curve[-1])
    return out


def _normalize(curve: list[Point]) -> list[Point]:
    outlined = _outline(curve)
    mx = sum(p[0] for p in outlined) / len(outlined)
    my = sum(p[1] for p in outlined) / len(outlined)
    t = [(p[0] - mx, p[1] - my) for p in outlined]
    scale = math.sqrt(((t[0][0] ** 2 + t[0][1] ** 2) + (t[-1][0] ** 2 + t[-1][1] ** 2)) / 2)
    if scale == 0:
        return t
    return _subdivide([(p[0] / scale, p[1] / scale) for p in t])


def _rotate(curve: list[Point], theta: float) -> list[Point]:
    c, s = math.cos(theta), math.sin(theta)
    return [(c * x - s * y, s * x + c * y) for x, y in curve]


@dataclass
class _Match:
    is_match: bool
    avg_dist: float
    backwards: bool = False


def _avg_distance(stroke: list[Point], points: list[Point]) -> float:
    return sum(min(_dist(sp, p) for sp in stroke) for p in points) / len(points)


def _match_data(points: list[Point], stroke: list[Point], stroke_num: int, leniency: float,
                outline_visible: bool, check_backwards: bool = True) -> _Match:
    avg = _avg_distance(stroke, points)
    dist_mod = 0.5 if outline_visible or stroke_num > 0 else 1.0
    if avg > AVERAGE_DISTANCE_THRESHOLD * dist_mod * leniency:
        return _Match(False, avg)
    start_end = (_dist(stroke[0], points[0]) <= START_AND_END_DIST_THRESHOLD * leniency
                 and _dist(stroke[-1], points[-1]) <= START_AND_END_DIST_THRESHOLD * leniency)
    stroke_vecs = _vectors(stroke)
    sims = []
    for ev in _vectors(points):
        cs = [_cosine(sv, ev) for sv in stroke_vecs]
        # JS Math.max(...) is NaN if any input is NaN; Python's max() isn't.
        sims.append(float("nan") if not cs or any(math.isnan(c) for c in cs) else max(cs))
    direction = (sum(sims) / len(sims)) > COSINE_SIMILARITY_THRESHOLD if sims else False
    n1, n2 = _normalize(points), _normalize(stroke)
    shape = min(_frechet(n1, _rotate(n2, th)) for th in SHAPE_FIT_ROTATIONS) <= FRECHET_THRESHOLD * leniency
    length_ok = leniency * (_length(points) + 25) / (_length(stroke) + 25) >= MIN_LEN_THRESHOLD
    is_match = start_end and direction and shape and length_ok
    if check_backwards and not is_match:
        back = _match_data(points[::-1], stroke, stroke_num, leniency, outline_visible, check_backwards=False)
        if back.is_match:
            return _Match(False, avg, backwards=True)
    return _Match(is_match, avg)


def _strip_duplicates(points: list[Point]) -> list[Point]:
    out = points[:1]
    for p in points[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def stroke_matches(points: list[Point], medians: list[list[Point]], stroke_num: int,
                   leniency: float = SERVER_LENIENCY, outline_visible: bool = True) -> bool:
    """hanzi-writer's strokeMatches(): does this drawn stroke match stroke
    `stroke_num`, and not fit a later stroke clearly better?"""
    pts = _strip_duplicates(points)
    if len(pts) < 2:
        return False
    first = _match_data(pts, medians[stroke_num], stroke_num, leniency, outline_visible)
    if not first.is_match:
        return False
    closest = first.avg_dist
    for later_num in range(stroke_num + 1, len(medians)):
        m = _match_data(pts, medians[later_num], later_num, leniency, outline_visible, check_backwards=False)
        if m.is_match and m.avg_dist < closest:
            closest = m.avg_dist
    if closest < first.avg_dist:
        adjust = 0.6 * (closest + first.avg_dist) / (2 * first.avg_dist)
        return _match_data(pts, medians[stroke_num], stroke_num, leniency * adjust, outline_visible).is_match
    return True


# ------------------------------------------------------------------ whole trace

MAX_DRAWN_STROKES_FACTOR = 6     # a learner may miss each stroke a few times
MAX_POINTS_PER_STROKE = 600
COORD_MIN, COORD_MAX = -600.0, 1700.0  # the 1024-unit box plus generous margins


class TraceRejected(Exception):
    pass


def medians_of(stroke_data: dict) -> list[list[Point]]:
    return [[(float(x), float(y)) for x, y in stroke] for stroke in stroke_data["medians"]]


def verify_trace(stroke_data: dict, drawn: list[dict]) -> int:
    """Replays the quiz over the drawn strokes and returns the number of
    mistakes. `drawn` is [{"points": [[x, y], ...], "matched": bool}, ...]
    in drawing order. Every stroke the browser counted as matched must
    really match the next expected stroke here; the matched ones must cover
    every stroke of the character, in order, and nothing may follow the
    last one. Strokes the browser counted as misses are mistakes (a client
    that under-reports its own success only lowers its own gain)."""
    medians = medians_of(stroke_data)
    n = len(medians)
    if not drawn:
        raise TraceRejected("No strokes were drawn")
    if len(drawn) > n * MAX_DRAWN_STROKES_FACTOR + 10:
        raise TraceRejected("Too many strokes for this character")
    expected = 0
    mistakes = 0
    for i, s in enumerate(drawn):
        if expected >= n:
            raise TraceRejected("Strokes were sent after the character was complete")
        pts = s["points"]
        if not (2 <= len(pts) <= MAX_POINTS_PER_STROKE):
            raise TraceRejected("A stroke has an invalid number of points")
        for x, y in pts:
            if not (math.isfinite(x) and math.isfinite(y)) or not (COORD_MIN <= x <= COORD_MAX and COORD_MIN <= y <= COORD_MAX):
                raise TraceRejected("A stroke point is outside the character box")
        if s["matched"]:
            fpts = [(float(x), float(y)) for x, y in pts]
            if not (stroke_matches(fpts, medians, expected)
                    or stroke_matches(fpts, medians, expected, leniency=ROUNDING_LENIENCY)):
                raise TraceRejected(f"Stroke {expected + 1} does not match the character's stroke")
            expected += 1
        else:
            mistakes += 1
    if expected != n:
        raise TraceRejected("The character was not traced to the end")
    return mistakes
