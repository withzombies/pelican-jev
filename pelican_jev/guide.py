"""A compact, hand-authored guide that keeps Jev's strokes recognizable."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, cos, hypot, pi, sin

Point = tuple[float, float]

INK = "#263b52"
BIKE = "#237f98"
ORANGE = "#d66a35"


@dataclass(frozen=True)
class Stroke:
    part: str
    points: tuple[Point, ...]
    color: str = INK
    width: int = 5


def _sample_line(points: tuple[Point, ...], maximum: float = 45) -> tuple[Point, ...]:
    result = [points[0]]
    for start, end in zip(points[:-1], points[1:], strict=True):
        count = max(1, ceil(hypot(end[0] - start[0], end[1] - start[1]) / maximum))
        result.extend(
            (
                start[0] + (end[0] - start[0]) * index / count,
                start[1] + (end[1] - start[1]) * index / count,
            )
            for index in range(1, count + 1)
        )
    return tuple(result)


def _curve(start: Point, c1: Point, c2: Point, end: Point, count: int = 6) -> tuple[Point, ...]:
    points = []
    for index in range(count + 1):
        t = index / count
        s = 1 - t
        points.append(
            (
                s**3 * start[0] + 3 * s**2 * t * c1[0] + 3 * s * t**2 * c2[0] + t**3 * end[0],
                s**3 * start[1] + 3 * s**2 * t * c1[1] + 3 * s * t**2 * c2[1] + t**3 * end[1],
            )
        )
    return tuple(points)


def _circle(cx: float, cy: float, radius: float, count: int = 32) -> tuple[Point, ...]:
    return tuple(
        (cx + radius * cos(2 * pi * index / count), cy + radius * sin(2 * pi * index / count))
        for index in range(count + 1)
    )


def _stroke(part: str, points: tuple[Point, ...], color: str = INK, width: int = 5) -> Stroke:
    return Stroke(part, _sample_line(points), color, width)


def build_strokes() -> tuple[Stroke, ...]:
    """Return ordered paths for a 960x720 drawing canvas, bicycle first."""
    rear = (255.0, 520.0)
    front = (715.0, 520.0)
    seat = (425.0, 365.0)
    crank = (490.0, 520.0)
    head = (620.0, 365.0)
    strokes = [
        _stroke("rear_wheel", _circle(*rear, 125), BIKE, 6),
        _stroke("front_wheel", _circle(*front, 125), BIKE, 6),
        _stroke("frame", (rear, seat, crank, rear), BIKE, 6),
        _stroke("frame", (seat, head, crank), BIKE, 6),
        _stroke("fork", (head, front), BIKE, 6),
        _stroke("handlebar", (head, (611, 332), (640, 318), (671, 321)), BIKE, 6),
        _stroke("saddle", ((388, 351), (425, 348), (455, 351)), BIKE, 7),
        _stroke("pedal", ((474, 520), (506, 520), (524, 537)), BIKE, 5),
        _stroke("rear_spoke", (rear, (255, 395)), BIKE, 3),
        _stroke("rear_spoke", (rear, (255, 645)), BIKE, 3),
        _stroke("rear_spoke", (rear, (130, 520)), BIKE, 3),
        _stroke("front_spoke", (front, (715, 395)), BIKE, 3),
        _stroke("front_spoke", (front, (715, 645)), BIKE, 3),
        _stroke("front_spoke", (front, (840, 520)), BIKE, 3),
    ]
    body = (
        _curve((318, 274), (352, 211), (468, 208), (520, 264))
        + _curve((520, 264), (570, 320), (519, 363), (438, 357))[1:]
        + _curve((438, 357), (373, 352), (331, 327), (318, 274))[1:]
    )
    neck = (
        _curve((505, 274), (525, 241), (519, 172), (563, 151))
        + _curve((563, 151), (588, 133), (618, 149), (628, 181))[1:]
        + _curve((628, 181), (639, 205), (622, 224), (588, 224))[1:]
        + _curve((588, 224), (561, 224), (558, 277), (546, 307))[1:]
    )
    wing = (
        _curve((358, 280), (401, 253), (466, 266), (511, 306))
        + _curve((511, 306), (459, 340), (398, 338), (358, 280))[1:]
    )
    beak = (
        _curve((625, 185), (679, 187), (742, 197), (789, 207))
        + _curve((789, 207), (742, 218), (679, 221), (623, 219))[1:]
    )
    pouch = (
        _curve((623, 219), (676, 225), (739, 224), (789, 207))
        + _curve((789, 207), (762, 281), (699, 306), (655, 284))[1:]
        + _curve((655, 284), (633, 273), (626, 243), (623, 219))[1:]
    )
    strokes.extend(
        [
            _stroke("body", body, INK, 6),
            _stroke("tail", ((335, 272), (297, 246), (314, 286), (286, 278)), INK, 5),
            _stroke("neck", neck, INK, 6),
            _stroke("wing", wing, INK, 5),
            _stroke("wing_feather", ((394, 300), (427, 312), (461, 310)), INK, 3),
            _stroke("beak", beak, ORANGE, 6),
            _stroke("pouch", pouch, ORANGE, 5),
            _stroke("eye", _circle(594, 177, 5, 12), INK, 5),
            _stroke("feet", ((422, 350), (443, 410), (474, 499), (490, 507)), ORANGE, 5),
            _stroke("feet", ((475, 350), (479, 407), (507, 490), (527, 532)), ORANGE, 5),
            _stroke("toe", ((476, 507), (498, 507)), ORANGE, 4),
            _stroke("toe", ((515, 532), (538, 532)), ORANGE, 4),
        ]
    )
    return tuple(strokes)
