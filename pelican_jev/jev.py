"""Small, testable client for TypeSafe's typed Jev choice API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from typing import Any

API_URL = "https://api.typesafe.ai/v1/systemone"
INSTRUCTIONS = (
    "Choose the next Logo turtle move that keeps the current part smooth and recognizable. "
    "Favor a natural contour and vary choices when useful."
)


class JevError(RuntimeError):
    """Base exception for a Jev decision failure."""


class TemporaryJevError(JevError):
    """A timeout, network fault, rate limit, or server fault that may clear."""


class PermanentJevError(JevError):
    """Missing access or a rejected request requiring a person to fix it."""


class InvalidJevResponse(JevError):
    """A response that cannot be used as a bounded turtle choice."""


@dataclass(frozen=True)
class Decision:
    choice: str
    confidence: float
    model: str
    probabilities: dict[str, float]


Transport = Callable[[dict[str, Any]], dict[str, Any]]


class JevClient:
    def __init__(
        self,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        model: str = "jev-latest",
    ) -> None:
        self.transport = transport or self._http_post
        self.sleep = sleep
        self.model = model

    def choose(
        self,
        state: dict[str, Any],
        criteria: dict[str, str],
        *,
        instructions: str = INSTRUCTIONS,
    ) -> Decision:
        if not criteria:
            raise ValueError("Jev needs at least one offered move")
        payload = {
            "state": state,
            "model": self.model,
            "questions": {
                "move": {"type": "choice", "instructions": instructions, "criteria": criteria}
            },
        }
        for attempt in range(3):
            try:
                response = self.transport(payload)
                break
            except TemporaryJevError:
                if attempt == 2:
                    raise
                self.sleep(0.5 * 2**attempt)
        if not isinstance(response, dict):
            raise InvalidJevResponse("Jev response is not an object")
        answers = response.get("answers")
        answer = answers.get("move") if isinstance(answers, dict) else None
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise InvalidJevResponse("Jev did not return a choice answer")
        choice = answer.get("choice")
        if choice not in criteria:
            raise InvalidJevResponse("Jev returned an unoffered move")
        confidence = answer.get("confidence")
        if (
            not isinstance(confidence, int | float)
            or isinstance(confidence, bool)
            or not isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise InvalidJevResponse("Jev returned invalid confidence")
        raw_probabilities = answer.get("probabilities")
        probabilities = {}
        if isinstance(raw_probabilities, dict):
            probabilities = {
                name: float(value)
                for name, value in raw_probabilities.items()
                if name in criteria
                and isinstance(value, int | float)
                and not isinstance(value, bool)
                and isfinite(value)
                and 0 <= value <= 1
            }
        model = response.get("model")
        return Decision(
            choice,
            float(confidence),
            model if isinstance(model, str) else self.model,
            probabilities,
        )

    @staticmethod
    def _http_post(payload: dict[str, Any]) -> dict[str, Any]:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            raise PermanentJevError("Set TYPESAFE_API_KEY to run live Jev decisions")
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code >= 500:
                raise TemporaryJevError(f"Jev API returned HTTP {error.code}") from error
            raise PermanentJevError(f"Jev API rejected the request: HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise TemporaryJevError("Could not reach Jev API") from error
        except json.JSONDecodeError as error:
            raise InvalidJevResponse("Jev API returned invalid JSON") from error
