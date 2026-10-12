import pytest

from form import GRADES, LANGUAGE_CHOICES, validate_form
from suggest import Request


def ok(grade="1", language="English", levels=None, interests="dragons"):
    return validate_form(grade, language, {"English": 1.5} if levels is None else levels, interests)


def test_complete_english_form_gives_a_request():
    request, errors = ok()
    assert errors == []
    assert request == Request(grade="1", levels={"English": 1.5}, interests="dragons")


def test_spanish_only_keeps_just_the_spanish_level():
    request, errors = validate_form("2", "Spanish", {"English": 2.0, "Spanish": 3.5}, "dinosaurs")
    assert errors == [] and request.levels == {"Spanish": 3.5}


def test_both_languages_keep_each_level_separately():
    request, errors = validate_form("1", "Both", {"English": 1.0, "Spanish": 3.0}, "dragons")
    assert errors == [] and request.levels == {"English": 1.0, "Spanish": 3.0}


@pytest.mark.parametrize("grade", GRADES)
def test_every_grade_from_k_to_5_is_accepted(grade):
    assert ok(grade=grade)[1] == []


@pytest.mark.parametrize("grade", [None, "", "6", "0", "Kindergarten", 1])
def test_missing_or_unknown_grade_is_an_error(grade):
    request, errors = ok(grade=grade)
    assert request is None and "grade" in errors[0].lower()


@pytest.mark.parametrize("language", [None, "", "French", "english"])
def test_unknown_language_choice_is_an_error(language):
    request, errors = validate_form("1", language, {"English": 1.0}, "dragons")
    assert request is None and any("English, Spanish, or both" in e for e in errors)


def test_a_level_is_required_for_each_chosen_language():
    request, errors = validate_form("1", "Both", {"English": 1.0, "Spanish": None}, "dragons")
    assert request is None and errors == ["Please enter the reading level in Spanish."]


def test_a_level_for_an_unchosen_language_is_ignored_even_if_missing():
    assert validate_form("1", "English", {"English": 1.0, "Spanish": None}, "dragons")[1] == []


@pytest.mark.parametrize("level", [None, "2.5", True, [2.0]])
def test_non_numbers_are_not_levels(level):
    request, errors = ok(levels={"English": level})
    assert request is None and "reading level in English" in errors[0]


@pytest.mark.parametrize("level", [-0.1, 13.0, 100])
def test_levels_outside_the_star_range_are_errors(level):
    request, errors = ok(levels={"English": level})
    assert request is None and "between 0.0 and 12.9" in errors[0]


@pytest.mark.parametrize("level", [0.0, 0.5, 12.9, 3])
def test_levels_at_the_edges_are_fine(level):
    request, errors = ok(levels={"English": level})
    assert errors == [] and request.levels == {"English": float(level)}


@pytest.mark.parametrize("interests", ["", "   ", None, "\n\t"])
def test_interests_are_required(interests):
    request, errors = ok(interests=interests)
    assert request is None and errors == ["Please tell us at least one thing your child likes."]


def test_interests_are_tidied():
    assert ok(interests="  dragons   and \n soccer ")[0].interests == "dragons and soccer"


def test_interests_of_exactly_200_characters_are_fine_and_201_is_not():
    assert ok(interests="a" * 200)[1] == []
    assert "200 characters" in ok(interests="a" * 201)[1][0]


def test_all_problems_are_reported_together():
    request, errors = validate_form(None, "Both", {}, "")
    assert request is None and len(errors) == 4
    assert LANGUAGE_CHOICES["Both"] == ("English", "Spanish")
