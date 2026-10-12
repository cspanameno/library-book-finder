"""Check what the parent typed in the form and turn it into a Request."""
from suggest import MAX_INTERESTS_CHARS, Request

GRADES = ("K", "1", "2", "3", "4", "5")
LANGUAGE_CHOICES = {
    "English": ("English",),
    "Spanish": ("Spanish",),
    "Both": ("English", "Spanish"),
}
LEVEL_MIN, LEVEL_MAX = 0.0, 12.9  # the range of a Star Grade Equivalent


def validate_form(grade, language_choice, levels, interests):
    """Return (Request, []) when the form is complete, or (None, [messages]).

    `levels` maps each language to the number the parent typed (or None).
    Only the selected languages' levels go into the Request.
    """
    errors = []
    if grade not in GRADES:
        errors.append("Please choose your child's grade.")

    languages = LANGUAGE_CHOICES.get(language_choice)
    if languages is None:
        errors.append("Please choose English, Spanish, or both.")
        languages = ()

    chosen_levels = {}
    for language in languages:
        level = (levels or {}).get(language)
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            errors.append(f"Please enter the reading level in {language}.")
        elif not LEVEL_MIN <= level <= LEVEL_MAX:
            errors.append(f"The reading level in {language} should be between {LEVEL_MIN} and {LEVEL_MAX}.")
        else:
            chosen_levels[language] = float(level)

    text = " ".join((interests or "").split())
    if not text:
        errors.append("Please tell us at least one thing your child likes.")
    elif len(text) > MAX_INTERESTS_CHARS:
        errors.append(f"Please keep the interests under {MAX_INTERESTS_CHARS} characters.")

    if errors:
        return None, errors
    return Request(grade=grade, levels=chosen_levels, interests=text), []
