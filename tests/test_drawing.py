from __future__ import annotations

from math import hypot

from pelican_jev.guide import build_strokes
from pelican_jev.turtle import Turtle, candidate_moves


def test_guide_has_bicycle_and_pelican_parts() -> None:
    strokes = build_strokes()
    parts = {stroke.part for stroke in strokes}
    required = {
        "rear_wheel", "front_wheel", "frame", "body", "neck", "beak", "pouch", "wing", "feet"
    }
    assert required <= parts
    assert all(len(stroke.points) >= 2 for stroke in strokes)


def test_guide_fits_a_watchable_live_decision_budget() -> None:
    moves = sum(len(stroke.points) - 1 for stroke in build_strokes())
    assert moves <= 240


def test_candidate_endpoints_stay_near_guide() -> None:
    turtle = Turtle()
    for stroke in build_strokes():
        turtle.reposition(stroke.points[0])
        for index in range(1, len(stroke.points)):
            moves = candidate_moves(stroke, index, turtle)
            assert set(moves) == {"left", "center", "right"}
            target = stroke.points[index]
            assert all(
                hypot(move.end[0] - target[0], move.end[1] - target[1]) <= 6.01
                for move in moves.values()
            )
            turtle.advance(moves["left"], stroke)


def test_turtle_applies_turn_and_forward() -> None:
    turtle = Turtle(x=10, y=10, heading=0)
    stroke = build_strokes()[0]
    turtle.reposition((10, 10))
    segment = turtle.advance_to((10, 20), stroke)
    assert round(segment.turn_degrees) == 90
    assert round(segment.forward_pixels) == 10
    assert segment.start == (10, 10)
    assert segment.end == (10, 20)


def test_wheel_paths_close_even_with_left_choices() -> None:
    turtle = Turtle()
    wheels = [stroke for stroke in build_strokes() if stroke.part.endswith("wheel")]
    assert len(wheels) == 2
    for stroke in wheels:
        turtle.reposition(stroke.points[0])
        for index in range(1, len(stroke.points)):
            turtle.advance(candidate_moves(stroke, index, turtle)["left"], stroke)
        assert hypot(turtle.x - stroke.points[0][0], turtle.y - stroke.points[0][1]) < 0.001
