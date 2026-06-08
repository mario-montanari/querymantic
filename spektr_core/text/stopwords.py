"""Function-word stop lists for entity extraction.

These are deliberately small lists of grammatical function words (articles,
prepositions, conjunctions, pronouns, common auxiliaries, and question words) for
the languages the suite supports. They strip non-entity tokens from keyword
phrases without removing meaningful modifiers such as "best" or "cheap", which
carry commercial intent.

The lists are basic and extensible, not a linguistic resource. A caller can pass
extra stopwords to the tokenizer for a specific corpus. Italian is added when the
suite gains its fifth language.
"""

from __future__ import annotations

_EN = """
a an the this that these those of in on at to from by for with without about into
over under again further then once and or but nor so as is are was were be been
being do does did has have had i you he she it we they me him her them my your his
its our their what which who whom how when where why whether if not no yes than too
very can will just don should now vs versus
""".split()

_FR = """
le la les un une des du de au aux et ou mais donc ni car a dans sur sous par pour
avec sans ce cet cette ces mon ton son notre votre leur je tu il elle nous vous ils
elles que qui quoi comment quand ou pourquoi ne pas plus est sont etre avoir
""".split()

_DE = """
der die das ein eine den dem des und oder aber doch als wie wenn weil dass in an auf
zu von mit ohne fur uber unter ich du er sie es wir ihr was wer wie wann wo warum
nicht kein ist sind sein haben werden
""".split()

_ES = """
el la los las un una unos unas de del al y o pero ni porque que como cuando donde por
para con sin en sobre bajo este esta estos estas mi tu su nuestro vuestro yo tu el
ella nosotros que quien como cuando donde por que no si es son ser haber muy mas
""".split()

STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(_EN),
    "fr": frozenset(_FR),
    "de": frozenset(_DE),
    "es": frozenset(_ES),
}

# Used when a keyword's language is unknown or unsupported: the union of all lists,
# so extraction still strips obvious function words.
_ALL = frozenset().union(*STOPWORDS.values())


def stopwords_for(language: str) -> frozenset[str]:
    """Return the stop list for an ISO 639-1 code, or the union when unknown."""
    return STOPWORDS.get((language or "").lower(), _ALL)
