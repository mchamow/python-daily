import random
from collections.abc import Callable, Iterator

import pytest

from py_terminal_quiz.answers import Verdict, judge, points
from py_terminal_quiz.game import play, summary
from py_terminal_quiz.questions import Difficulty, Question

ICELAND = Question("Geography", Difficulty.MEDIUM, "Capital of Iceland?", ("Reykjavík",))
CURIE = Question("History", Difficulty.MEDIUM, "First woman Nobel?", ("Maria Skłodowska-Curie",))
FLOOR = Question("Python", Difficulty.MEDIUM, "-7 // 2?", ("-4",))
CSV = Question("Computing", Difficulty.EASY, "CSV?", ("Comma-separated values",))
STRASSE = Question("German", Difficulty.EASY, "Street?", ("Straße",))
WALL = Question("History", Difficulty.EASY, "Berlin Wall fell?", ("1989",), ("1987", "1991"))


@pytest.mark.parametrize(
    ("question", "reply", "options", "verdict"),
    [
        (ICELAND, "  REYKJAVIK ", [], Verdict.CORRECT),  # case, spaces and accents ignored
        (ICELAND, "Reykjavic", [], Verdict.TYPO),
        (ICELAND, "Oslo", [], Verdict.WRONG),
        (CURIE, "maria skłodowska curie", [], Verdict.CORRECT),  # hyphen == space
        (CURIE, "Maria Sklodowska-Curie", [], Verdict.TYPO),  # NFKD keeps ł: it isn't an accent
        (WALL, "1988", [], Verdict.WRONG),  # no typo tolerance for numbers
        (WALL, "c", ["1987", "1991", "1989"], Verdict.CORRECT),  # a letter picks an option
        (WALL, "a", ["1987", "1991", "1989"], Verdict.WRONG),
        (WALL, "", ["1987", "1991", "1989"], Verdict.SKIPPED),
        (FLOOR, "4", [], Verdict.WRONG),  # the minus sign survives normalisation
        (CSV, "comma separated VALUES!", [], Verdict.CORRECT),
        (STRASSE, "STRASSE", [], Verdict.CORRECT),  # casefold() knows ß == ss; lower() doesn't
    ],
)
def test_judge(question: Question, reply: str, options: list[str], verdict: Verdict) -> None:
    assert judge(question, reply, options)[0] is verdict


@pytest.mark.parametrize(
    ("seconds", "difficulty", "streak", "expected"),
    [
        (0.0, Difficulty.EASY, 1, 1000),
        (10.0, Difficulty.EASY, 1, 750),  # halfway through a 20 s limit
        (20.0, Difficulty.HARD, 1, 1000),  # at the buzzer: half of 2000
        (20.1, Difficulty.HARD, 3, 0),
        (0.0, Difficulty.MEDIUM, 3, 1700),  # 1500 + 2 x 100 streak bonus
        (0.0, Difficulty.EASY, 50, 1500),  # bonus capped at 500
    ],
)
def test_points(seconds: float, difficulty: Difficulty, streak: int, expected: int) -> None:
    assert points(seconds, 20, difficulty, streak) == expected


def scripted(replies: list[str]) -> Callable[[str], str]:
    """Stand-in for input(): hands out the replies, then behaves like Ctrl-D."""
    it = iter(replies)

    def ask(prompt: str) -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    return ask


def fake_clock(*durations: float) -> Callable[[], float]:
    """Each answer takes the next duration: the clock alternates between start and stop."""

    def ticks() -> Iterator[float]:
        now = 0.0
        for d in durations:
            yield now
            now += d
            yield now

    return ticks().__next__


def test_play_times_judges_and_scores_each_answer() -> None:
    printed: list[str] = []
    answers = play(
        [ICELAND, ICELAND, CURIE, ICELAND],
        random.Random(0),
        limit=10,
        ask=scripted(["reykjavik", "Reykjavík", "curie?", "reykjavik"]),
        say=printed.append,
        clock=fake_clock(2.0, 0.0, 3.0, 12.5),
    )
    assert [a.verdict for a in answers] == [
        Verdict.CORRECT,
        Verdict.CORRECT,
        Verdict.WRONG,
        Verdict.SLOW,  # right answer, after the limit
    ]
    assert [a.seconds for a in answers] == [2.0, 0.0, 3.0, 12.5]
    assert [a.points for a in answers] == [1350, 1600, 0, 0]  # the second has a streak bonus
    assert "✓ Reykjavík  +1,600  (0.0s, streak 2)" in printed
    assert summary(answers).splitlines()[0] == "Score 2,950 · 2/4 correct · median answer 2.5s"


def test_end_of_input_and_quit_stop_the_game_early() -> None:
    quiz = [WALL, WALL, WALL]
    eof = play(quiz, random.Random(1), limit=10, ask=scripted(["1989"]), say=lambda _: None)
    assert len(eof) == 1
    quit_ = play(quiz, random.Random(1), limit=10, ask=scripted([":q"]), say=lambda _: None)
    assert quit_ == []
    assert summary(quit_) == "No questions answered."
