"""The quiz loop: ask, time, judge, score. Input, output and the clock are all injectable."""

import random
import statistics
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from string import ascii_uppercase

from .answers import Verdict, judge, points
from .questions import Question, shuffled_options

QUIT = {":q", ":quit"}


@dataclass(frozen=True, slots=True)
class Answer:
    question: Question
    reply: str
    verdict: Verdict
    seconds: float
    points: int


def play(
    questions: Sequence[Question],
    rng: random.Random,
    *,
    limit: float,
    ask: Callable[[str], str] = input,
    say: Callable[[str], object] = print,
    clock: Callable[[], float] = time.perf_counter,
) -> list[Answer]:
    """Play through ``questions`` and return one Answer per question asked.

    Stops early on ':q' or end of input (Ctrl-D), keeping the answers so far.
    """
    answers: list[Answer] = []
    streak = 0
    for number, question in enumerate(questions, start=1):
        options = shuffled_options(question, rng)
        say(f"\n[{number}/{len(questions)}] {question.category} · {question.difficulty}")
        say(question.text)
        if options:
            # strict=False on purpose: 26 letters, at most 6 options (zip stops at the shorter).
            labelled = zip(ascii_uppercase, options, strict=False)
            say("  " + "    ".join(f"{letter}) {option}" for letter, option in labelled))
        start = clock()  # perf_counter: monotonic and high-resolution, i.e. a Stopwatch
        try:
            reply = ask("> ")
        except EOFError:
            say("")
            break
        seconds = clock() - start
        if reply.strip().lower() in QUIT:
            break
        verdict, chosen = judge(question, reply, options)
        if verdict.scores and seconds > limit:
            verdict = Verdict.SLOW
        streak = streak + 1 if verdict.scores else 0
        earned = points(seconds, limit, question.difficulty, streak) if verdict.scores else 0
        answers.append(Answer(question, chosen, verdict, seconds, earned))
        say(feedback(answers[-1], streak, limit))
    return answers


def feedback(answer: Answer, streak: int, limit: float) -> str:
    q, took = answer.question, f"{answer.seconds:.1f}s"
    match answer.verdict:
        case Verdict.CORRECT:
            extra = f", streak {streak}" if streak > 1 else ""
            return f"✓ {q.answer}  +{answer.points:,}  ({took}{extra})"
        case Verdict.TYPO:
            return f"✓ {q.answer}, close enough to {answer.reply!r}  +{answer.points:,}  ({took})"
        case Verdict.SLOW:
            return f"⏱ Right, but too slow: {took} (limit {limit:g}s). No points."
        case Verdict.SKIPPED:
            return f"→ Skipped. It was {q.answer}."
        case Verdict.WRONG:
            return f"✗ It was {q.answer}  (you said {answer.reply!r}, {took})"


def summary(answers: Sequence[Answer]) -> str:
    if not answers:
        return "No questions answered."
    total = sum(a.points for a in answers)
    right = [a for a in answers if a.verdict.scores]
    times = [a.seconds for a in answers if a.verdict is not Verdict.SKIPPED]
    lines = [f"Score {total:,} · {len(right)}/{len(answers)} correct"]
    if times:
        lines[0] += f" · median answer {statistics.median(times):.1f}s"
    if right:
        best = min(right, key=lambda a: a.seconds)
        lines.append(f"Fastest right answer: {best.seconds:.1f}s, {best.question.answer!r}")
    asked = Counter(a.question.category for a in answers)
    scored = Counter(a.question.category for a in right)
    # asked's keys come out in first-seen order: dicts (and Counters) keep insertion order.
    lines.append("By category: " + " · ".join(f"{c} {scored[c]}/{n}" for c, n in asked.items()))
    return "\n".join(lines)
