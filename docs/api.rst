.. _api_page:


BELA API reference
==================

For most people, :func:`bela.read_eaf` is the first thing to look at.
This function returns a :class:`bela.Bela2` object for manipulating
a BELA transcript directly:

>>> import bela
>>> b2 = bela.read_eaf("my_bela_filename.eaf")

Now you can use the created ``b2`` object to process BELA data.

>>> for person in b2.persons:
>>>     print(person.name, person.code)
>>>     for u in person.utterances:
>>>         print(u, u.from_ts, u.to_ts, u.duration)
>>>         if u.translation:
>>>             print(u.translation)
>>>         for c in u.chunks:
>>>             print(f"  - {c} [{c.language}]")

The bela module
---------------

.. module:: bela

.. autofunction:: read_eaf

.. autofunction:: from_elan


The lex module
--------------

.. module:: bela.lex

This module provides lexicon analysis functions
(i.e. counting tokens, calculating class-token ratio, et cetera).
New users should start with :class:`bela.lex.CorpusLexicalAnalyser`.

>>> from bela.lex import CorpusLexicalAnalyser
>>> analyser = CorpusLexicalAnalyser()
>>> for person in b2.persons:
>>>     for u in person.utterances:
>>>         analyser.add(u.text, u.language, source=source, speaker=person.code)
>>> analyser.analyse()


.. autoclass:: CorpusLexicalAnalyser
   :members: read, add, analyse, to_dict
   :member-order: groupwise


BELA-con version 2.0 API
-------------------------

The official Bela convention.
By default, this should be used for new transcripts.

.. autoclass:: bela.Bela2
   :members:
   :member-order: groupwise

BELA-con version 1.0 API
------------------------

Bela1 is deprecated from Mar 2020.
It is still available for backward compatible only.
Please do not use it for anything other than BLIP's PILOT10 corpus.

.. autoclass:: bela.Bela1
   :members:
   :member-order: groupwise
