"""Check what the parent chose in the form and turn it into a Request."""
from suggest import Request
from topics import BY_KEY, MAX_TOPICS, english_phrase, spanish_words

GRADES = ("K", "1", "2", "3", "4", "5")
LANGUAGE_CHOICES = {
    "English": ("English",),
    "Spanish": ("Spanish",),
    "Both": ("English", "Spanish"),
}
LEVEL_MIN, LEVEL_MAX = 0.0, 12.9  # the range of a Star Grade Equivalent


def validate_form(grade, language_choice, levels, topics):
    """Return (Request, []) when the form is complete, or (None, [messages]).

    `levels` maps each language to the number the parent typed (or None).
    Only the selected languages' levels go into the Request.
    `topics` is the list of chosen topic keys, e.g. ["dragons", "soccer"].
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

    chosen_topics = list(topics or [])
    if not chosen_topics:
        errors.append("Please pick at least one thing your child likes.")
    elif len(chosen_topics) > MAX_TOPICS:
        errors.append(f"Please pick up to {MAX_TOPICS} topics.")
    elif len(set(chosen_topics)) != len(chosen_topics) or any(
            not isinstance(key, str) or key not in BY_KEY for key in chosen_topics):
        errors.append("Please pick from the topics shown.")

    if errors:
        return None, errors
    return Request(grade=grade, levels=chosen_levels, interests=english_phrase(chosen_topics),
                   spanish_words=spanish_words(chosen_topics)), []
