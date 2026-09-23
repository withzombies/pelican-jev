"""Small Logo-style turtle with bounded Jev move proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, degrees, hypot, radians, sin

from .guide import Point, Stroke


@dataclass(frozen=True)
class Move:
    start: Point
    end: Point
    turn_degrees: float
    forward_pixels: float


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point
    turn_degrees: float
    forward_pixels: float
    part: str
    color: str
    width: int


@dataclass
class Turtle:
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    segments: list[Segment] = field(default_factory=list)

    def reposition(self, point: Point) -> None:
        """Travel to a stroke start with the pen up."""
        self.x, self.y = point

    def plan_to(self, end: Point) -> Move:
        start = (self.x, self.y)
        distance = hypot(end[0] - self.x, end[1] - self.y)
        absolute = degrees(atan2(end[1] - self.y, end[0] - self.x))
        turn = (absolute - self.heading + 180) % 360 - 180
        return Move(start, end, turn, distance)

    def advance(self, move: Move, stroke: Stroke) -> Segment:
        if hypot(self.x - move.start[0], self.y - move.start[1]) > 0.001:
            raise ValueError("move does not start at the turtle position")
        heading = (self.heading + move.turn_degrees) % 360
        calculated = (
            self.x + cos(radians(heading)) * move.forward_pixels,
            self.y + sin(radians(heading)) * move.forward_pixels,
        )
        if hypot(calculated[0] - move.end[0], calculated[1] - move.end[1]) > 0.001:
            raise ValueError("move endpoint disagrees with its turn and distance")
        segment = Segment(
            move.start, move.end, move.turn_degrees, move.forward_pixels,
            stroke.part, stroke.color, stroke.width,
        )
        self.x, self.y = move.end
        self.heading = heading
        self.segments.append(segment)
        return segment

    def advance_to(self, end: Point, stroke: Stroke) -> Segment:
        return self.advance(self.plan_to(end), stroke)


def candidate_moves(stroke: Stroke, point_index: int, turtle: Turtle) -> dict[str, Move]:
    """Offer three nearby endpoints, closing the path exactly at its last point."""
    if not 1 <= point_index < len(stroke.points):
        raise IndexError("point_index is outside this stroke")
    previous = stroke.points[point_index - 1]
    guide = stroke.points[point_index]
    dx, dy = guide[0] - previous[0], guide[1] - previous[1]
    length = hypot(dx, dy)
    if length == 0:
        raise ValueError("guide contains a zero-length segment")
    normal = (-dy / length, dx / length)
    offset = 0 if point_index == len(stroke.points) - 1 else 5
    return {
        name: turtle.plan_to(
            (guide[0] + sign * offset * normal[0], guide[1] + sign * offset * normal[1])
        )
        for name, sign in (("left", -1), ("center", 0), ("right", 1))
    }
