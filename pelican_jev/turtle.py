"""A bounded Logo turtle. Jev decides every command and parameter."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, degrees, radians, sin
from re import fullmatch

WIDTH = 960
HEIGHT = 720
DISTANCES = (10, 20, 40, 80, 120)
ANGLES = (15, 30, 45, 90, 120)
Point = tuple[float, float]


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point


@dataclass
class Turtle:
    x: float = WIDTH / 2
    y: float = HEIGHT / 2
    heading: float = 0.0
    pen_down: bool = False
    segments: list[Segment] = field(default_factory=list)

    def execute(self, command: str) -> None:
        target = fullmatch(r"SETXY_(\d{1,3})_(\d{1,3})", command)
        if target:
            x, y = (int(value) for value in target.groups())
            if not (24 <= x <= WIDTH - 24 and 24 <= y <= HEIGHT - 24):
                raise ValueError(f"command is unavailable: {command}")
            start = (self.x, self.y)
            if (x, y) != start:
                self.heading = degrees(atan2(y - self.y, x - self.x)) % 360
                self.x, self.y = x, y
                if self.pen_down:
                    self.segments.append(Segment(start, (x, y)))
            return
        if command not in available_commands(self):
            raise ValueError(f"command is unavailable: {command}")
        if command == "PENUP":
            self.pen_down = False
        elif command == "PENDOWN":
            self.pen_down = True
        elif command == "DONE":
            return
        else:
            action, amount_text = command.split("_")
            amount = int(amount_text)
            if action == "LEFT":
                self.heading = (self.heading - amount) % 360
            elif action == "RIGHT":
                self.heading = (self.heading + amount) % 360
            else:
                distance = amount if action == "FORWARD" else -amount
                start = (self.x, self.y)
                self.x += cos(radians(self.heading)) * distance
                self.y += sin(radians(self.heading)) * distance
                if self.pen_down:
                    self.segments.append(Segment(start, (self.x, self.y)))


def available_commands(turtle: Turtle) -> dict[str, str]:
    """All valid Logo actions at this pose; canvas bounds are the only filter."""
    options = {
        "PENUP": "Lift the pen; movement stops drawing lines.",
        "PENDOWN": "Lower the pen; movement draws lines.",
        "DONE": "Finish the drawing now.",
    }
    for action in ("FORWARD", "BACK"):
        for distance in DISTANCES:
            signed = distance if action == "FORWARD" else -distance
            x = turtle.x + cos(radians(turtle.heading)) * signed
            y = turtle.y + sin(radians(turtle.heading)) * signed
            if 24 <= x <= WIDTH - 24 and 24 <= y <= HEIGHT - 24:
                options[f"{action}_{distance}"] = f"{action} {distance} pixels."
    for action in ("LEFT", "RIGHT"):
        for angle in ANGLES:
            options[f"{action}_{angle}"] = f"Turn {action.lower()} {angle} degrees in place."
    return options
