import csv
import random
from pathlib import Path

import pytest

from py_terminal_quiz.questions import Difficulty, Question, RowError, load_questions, pick

DATA = Path(__file__).parent.parent / "data"


def test_bundled_files_load_with_quoting_and_multiline_fields() -> None:
    general = load_questions(DATA / "general.csv")
    python = load_questions(DATA / "python.csv")  # semicolon-separated: found by the Sniffer
    assert (len(general), len(python)) == (25, 12)
    danube = next(q for q in general if q.answer == "Danube")
    assert danube.text == "Which river flows through Vienna, Bratislava and Budapest?"
    dickens = next(q for q in general if q.answer == "A Tale of Two Cities")
    assert dickens.text.endswith('"It was the best of times, it was the worst of times"')
    rounding = next(q for q in python if q.answer == "2 4")
    assert rounding.text.splitlines()[-1] == "    print(round(2.5), round(3.5))"
    assert rounding.wrong == ("3 4", "2 3", "3 3")


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_any_common_delimiter_and_an_excel_bom(tmp_path: Path, delimiter: str) -> None:
    rows = [
        ["category", "difficulty", "question", "answer", "choices"],
        ["Maths", "Easy", "What is 6 * 7?", "42", "41|43"],
        ["Maths", "hard", "Name a prime, please", "2|3|5|7", ""],
    ]
    path = tmp_path / "quiz.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # -sig writes Excel's BOM
        csv.writer(f, delimiter=delimiter).writerows(rows)  # quotes "Name a prime, please"
    first, second = load_questions(path)
    assert first == Question("Maths", Difficulty.EASY, "What is 6 * 7?", ("42",), ("41", "43"))
    assert second.answers == ("2", "3", "5", "7")
    assert second.wrong == ()


def test_every_bad_row_is_reported_at_once_with_its_lines() -> None:
    with pytest.raises(ExceptionGroup) as caught:
        load_questions(DATA / "broken.csv")
    group = caught.value
    assert group.message == f"4 bad row(s) in {DATA / 'broken.csv'}"
    assert all(isinstance(e, RowError) for e in group.exceptions)
    messages = [str(e) for e in group.exceptions]
    assert messages[0].startswith("line 3: difficulty 'extreme'")
    assert messages[1] == "lines 4-5: no answer"  # a quoted field spans two physical lines
    assert messages[2] == "line 6: 'water' is both right and wrong"
    assert messages[3].startswith("line 7: 1 field(s) more than the header")


@pytest.fixture
def bank() -> list[Question]:
    return load_questions(DATA / "general.csv")


def test_the_same_seed_gives_the_same_quiz_easiest_first(bank: list[Question]) -> None:
    one = pick(bank, 8, random.Random("halloween"))
    two = pick(bank, 8, random.Random("halloween"))
    other = pick(bank, 8, random.Random("christmas"))
    assert one == two
    assert one != other
    ranks = [q.difficulty.rank for q in one]
    assert ranks == sorted(ranks)  # not sorted(difficulty): as strings "hard" < "medium"
    assert sorted(Difficulty) == [Difficulty.EASY, Difficulty.HARD, Difficulty.MEDIUM]


def test_filters_and_asking_for_more_than_there_are(bank: list[Question]) -> None:
    chosen = pick(bank, 100, random.Random(1), category="geography", difficulty=Difficulty.MEDIUM)
    assert len(chosen) == 3
    assert {(q.category, q.difficulty) for q in chosen} == {("Geography", Difficulty.MEDIUM)}
    with pytest.raises(LookupError, match="categories are: Computing, Geography"):
        pick(bank, 5, random.Random(1), category="Sport")
