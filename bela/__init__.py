# -*- coding: utf-8 -*-

"""
BLIP ELAN Language Annotation (BELA) package
"""

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

from .__version__ import __author__, __email__, __copyright__, __maintainer__
from .__version__ import __credits__, __license__, __description__, __url__
from .__version__ import __version_major__, __version_long__, __version__, __status__

from .common import maketime, getlang
from .common import is_special_token
from .common import process_text, tokenize
from .common import KNOWN_LANGUAGES, KNOWN_LANGUAGE_CLASSES
from .bela1 import Bela1
from .bela2 import Bela2, SPECIAL_SPEAKER, SPECIAL_SPEAKER_NAME


__all__ = ['Bela1', 'maketime', 'getlang', 'is_special_token',
           'process_token', 'process_text', 'tokenize',
           'KNOWN_LANGUAGES', 'KNOWN_LANGUAGE_CLASSES',
           'SPECIAL_SPEAKER', 'SPECIAL_SPEAKER_NAME',
           'Bela2',
           "__version__", "__author__", "__description__", "__copyright__"]
