import pytest

from display import display_author, display_title


@pytest.mark.parametrize("raw, shown", [
    ("Ven a la escuela, querido dragón = Come to school, dear dragon", "Ven a la escuela, querido dragón"),
    ("Brown bear, brown bear, what do you see? = Zong se de xiong", "Brown bear, brown bear, what do you see?"),
    ("Dragones y tacos 2 : la continuación", "Dragones y tacos 2: la continuación"),
    ("Los dragones adoran los calzoncillos", "Los dragones adoran los calzoncillos"),
    ("Oso pardo / Bill Martin", "Oso pardo"),
    ("  Fútbol   extremo ", "Fútbol extremo"),
    ("Ana, el dragón y la nube aspirador.", "Ana, el dragón y la nube aspirador"),
    ("¡Hora de fútbol!", "¡Hora de fútbol!"),
    ("¿Quién es?", "¿Quién es?"),
    ("A=B equals C", "A=B equals C"),      # an "=" with no spaces is part of the title
])
def test_display_title(raw, shown):
    assert display_title(raw) == shown


def test_a_title_that_is_only_a_parallel_title_keeps_the_original():
    assert display_title(" = Come to school") == "= Come to school"


@pytest.mark.parametrize("raw, shown", [
    ("Rubin, Adam, 1983- author.", "Adam Rubin"),
    ("Rubin, Adam, 1983-", "Adam Rubin"),
    ("Rubin, Adam", "Adam Rubin"),
    ("Freedman, Claire, author.", "Claire Freedman"),
    ("Cousins, Lucy, author, illustrator.", "Lucy Cousins"),
    ("Pilkey, Dav, 1966- author, illustrator.", "Dav Pilkey"),
    ("Troupe, Thomas Kingsley, author.", "Thomas Kingsley Troupe"),
    ("Boelts, Maribeth, 1964- author.", "Maribeth Boelts"),
    ("Sarrazin, Aurélie., author.", "Aurélie Sarrazin"),
    ("Willis, Val.", "Val Willis"),
    ("Martin, Bill, 1916-2004.", "Bill Martin"),
    ("Martin, Jr., Bill", "Bill Martin Jr."),
    ("King, Martin Luther, Jr.", "Martin Luther King Jr."),
    ("Seuss, Dr.", "Dr. Seuss"),
    ("Rowling, J. K.", "J. K. Rowling"),
    ("de la Cruz, Melissa, 1971-", "Melissa de la Cruz"),
    ("García Márquez, Gabriel, 1927-2014", "Gabriel García Márquez"),
    ("Raúl the Third, 1976- author, illustrator.", "Raúl the Third"),
    ("Rubin, Adam/ Salmieri, Daniel (ILT)/ Rubin, Adam (NRT)", "Adam Rubin"),
    ("Rubin, Adam (NRT)", "Adam Rubin"),
    ("Disney Press", "Disney Press"),
    ("Adam Rubin", "Adam Rubin"),
    ("Paolini, Christopher 1983-", "Christopher Paolini"),          # date without a comma
    ("Maddox, Jake. author.", "Jake Maddox"),                       # role after a period
    ("Brown, Dolores (Children's author)., author.", "Dolores Brown"),
    ("Terrell, Brandon, 1978-2021, author.", "Brandon Terrell"),
    ("Buckley, James, Jr., 1963- author.", "James Buckley Jr."),
    ("Vega, Eida de la, translator.", "Eida de la Vega"),
    ("Pelé, 1940- author.", "Pelé"),
    ("Scholastic Inc., editor.", "Scholastic Inc."),
])
def test_display_author(raw, shown):
    assert display_author(raw) == shown


@pytest.mark.parametrize("raw", ["", "   ", "/"])
def test_empty_author_does_not_crash(raw):
    assert display_author(raw) == raw.strip()


from display import level_text, md_escape


@pytest.mark.parametrize("raw, escaped", [
    ("Plain title", "Plain title"),
    ("Dragons *love* tacos", r"Dragons \*love\* tacos"),
    ("_Hello_ [link](http://x)", r"\_Hello\_ \[link\]\(http\://x\)"),
    ("Costs $5 and $10", r"Costs \$5 and \$10"),
    ("# Heading", r"\# Heading"),
    ("<b>bold</b>", r"\<b\>bold\</b\>"),
    ("Pelé's café ¿Qué?", r"Pelé's café ¿Qué?"),
])
def test_md_escape(raw, escaped):
    assert md_escape(raw) == escaped


@pytest.mark.parametrize("level, shown", [
    ("2.5", "grade 2.5"), ("3", "grade 3"), (" 1.0 ", "grade 1.0"),
    ("Grade 2", "Grade 2"), ("early second grade", "early second grade"), ("", ""), (None, ""),
])
def test_level_text(level, shown):
    assert level_text(level) == shown
