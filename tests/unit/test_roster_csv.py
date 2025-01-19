from __future__ import annotations

from datetime import date

from cleared.domain.roster_csv import parse_roster


def test_reads_a_clean_file() -> None:
    text = (
        "first_name,last_name,email,role_code,hired_on,status\n"
        "Marisol,Vega,marisol@example.com,cna,2024-03-04,active\n"
    )

    rows, problems = parse_roster(text)

    assert problems == []
    assert rows[0].first_name == "Marisol"
    assert rows[0].role_code == "CNA"
    assert rows[0].hired_on == date(2024, 3, 4)


def test_headers_are_case_and_space_insensitive() -> None:
    text = " First Name , Last Name \nAda,Lovelace\n"

    rows, problems = parse_roster(text)

    assert problems == []
    assert rows[0].last_name == "Lovelace"


def test_a_missing_column_is_one_problem_not_one_per_row() -> None:
    text = "first_name,email\nAda,ada@example.com\n"

    rows, problems = parse_roster(text)

    assert rows == []
    assert len(problems) == 1
    assert "last_name" in problems[0].message


def test_bad_rows_are_reported_with_their_line_number() -> None:
    text = (
        "first_name,last_name,email,hired_on,status\n"
        "Ada,Lovelace,not-an-email,,active\n"
        "Grace,Hopper,grace@example.com,04/03/2024,active\n"
        "Alan,Turing,alan@example.com,1912-06-23,retired\n"
        "Katherine,Johnson,,,active\n"
    )

    rows, problems = parse_roster(text)

    assert [row.last_name for row in rows] == ["Johnson"]
    assert [problem.line for problem in problems] == [2, 3, 4]


def test_quoted_values_with_commas_survive() -> None:
    text = 'first_name,last_name,location\nAda,Lovelace,"London, England"\n'

    rows, _ = parse_roster(text)

    assert rows[0].location == "London, England"


def test_an_empty_file_is_reported() -> None:
    rows, problems = parse_roster("")

    assert rows == []
    assert problems and problems[0].line == 1
