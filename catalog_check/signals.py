"""A signal is one piece of evidence about one attribute."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    attribute: str
    kind: str  # "support", "contradict", or "invalid"
    rule: str
    confidence: str  # "high" or "medium"
    value: str
    evidence: str
    explanation: str


def support(attribute: str, rule: str, confidence: str, value: str, evidence: str, explanation: str) -> Signal:
    return Signal(attribute, "support", rule, confidence, value, evidence, explanation)


def contradict(attribute: str, rule: str, confidence: str, value: str, evidence: str, explanation: str) -> Signal:
    return Signal(attribute, "contradict", rule, confidence, value, evidence, explanation)


def invalid(attribute: str, rule: str, value: str, explanation: str) -> Signal:
    return Signal(attribute, "invalid", rule, "high", value, "", explanation)
