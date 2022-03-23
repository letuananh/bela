=======
👸 BELA
=======

BELA (BLIP ELAN Language Annotation) is a pathway for creating and analysing multi-lingual
transcripts using `BELA convention <https://blipntu.github.io/belacon/>`_
and `ELAN software <https://archive.mpi.nl/tla/elan/download>`_.


Getting started
===============

BELA is available on `PyPI <https://pypi.org/project/bela/>`_ and can be installed using pip:

.. code-block:: bash

   pip install bela

Sample code
===========

The following code snippet reads a BELA transcript
and prints out all participants and their utterances & chunks.

.. code:: python

    import bela

    b2 = bela.read_eaf("my_bela_filename.eaf")
    for person in b2.persons:
        print(person.name, person.code)
        for u in person.utterances:
            print(u, u.from_ts, u.to_ts, u.duration)
            if u.translation:
                print(u.translation)
            for c in u.chunks:
                print(f"  - {c} [{c.language}]")


.. toctree::
   :maxdepth: 2
   :caption: Useful Links

   tutorials
   api
   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
