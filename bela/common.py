# -*- coding: utf-8 -*-

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

"""
Common functions
"""

import re
import logging
import string

try:
    from nltk import word_tokenize
    NLTK_AVAILABLE = True
except ModuleNotFoundError:
    NLTK_AVAILABLE = False
try:
    import jieba
    JIEBA_AVAILABLE = True
except ModuleNotFoundError:
    JIEBA_AVAILABLE = False
from speach.vtt import sec2ts


class InvalidTokenException(ValueError):
    ''' InvalidTokenException is raised when a text token is not a valid BELA token '''
    pass


# ... for ellipsis
PUNCS = list(string.punctuation) + list(' ，。？（）！') + ["؟"] + ['``', "''", '...']


def _remove_punc(tokens):
    return (x for x in tokens if x not in PUNCS)


def getLogger():
    return logging.getLogger(__name__)


def maketime(s):
    return f"{sec2ts(s.tsfrom)} - {sec2ts(s.tsto)} ({s.tsduration:02})"


def getlang(x):
    return x.strip() if x != 'N/A' else ''


def is_special_token(t):
    return "<" in t or ":" in t or "/" in t or "#" in t or "=" in t


KNOWN_LANGUAGES = ['English', 'Mandarin', 'Tamil', 'Cantonese', 'Malay', 'Javanese', 'Arabic', 'Hokkien', 'Red Dot']
# [2020-09-30] To take Interjection out of KNOWN_LANGUAGE_CLASSES to assign a label
KNOWN_LANGUAGE_CLASSES = ['Vocal Sounds', 'Non Vocal Sounds', 'Inaudible', 'Languageless', 'Interjection'] + [':v:airstream', ':v:crying', ':v:vocalizations', ':v:laughter']
UTTERANCE_GAP_THRESHOLD = 0.05
DEFAULT_NON_WORD = 'XbeepX'
TIER_PARSER = re.compile(r'(?P<person>[\w ]+) +\((?P<tier>[\w ]+)\)')
# usage
# m = TIER_PARSER.match('baby (Comments)')
BELA_CLASS_LABEL = re.compile("^[a-z0-9_]+$")
PTN_ELLIPSIS = re.compile(r'(\.{2,})$')
PTN_INNER_STOP = re.compile(r'\.+[^$\.?]+$')
VOCAL_CLOSED_CLASS = {
    'crying', 'kissing_sound', 'tsk', 'airstream', 'coughing',
    'animal_sound', 'flamingo_sound', 'orangutan_sound', 'elephant_sound',
    'lightning_sound', 'splash_sound', 'thunder_sound', 'rain_sound',
    'ringing_sound', 'screaming_sound', 'shushing_sound',
    'train_sound', 'gasp', 'laughter',
    'sigh', 'vocalizations', 'whistle', 'x'}
#  [2021-08-30 月 16:54] add 6 new vocal sounds
# 'flamingo_sound', 'orangutan_sound',
# 'lightning_sound ', 'splash_sound',
# 'ringing_sound', 'screaming_sound'
VOCAL_CLOSED_CLASS_3 = {'r', 'u'}
NON_VOCAL_SOUNDS = {'clapping', 'sneeze', 'clicking', 'sniff', 'sync', 'x'}


def _process_token(token, non_word=DEFAULT_NON_WORD, mimicked=False, word_only=True, **kwargs):
    ''' Extract text from a special ELAN token '''
    _res = [':m'] if mimicked and not word_only else []
    if token.startswith(":"):
        parts = [x for x in token.strip().split(":") if x]
        if not parts:
            raise InvalidTokenException("Token text is blank")
        elif parts[0] == 'v':
            if len(parts) == 2:
                if parts[1] in VOCAL_CLOSED_CLASS:
                    if word_only:
                        _res.append(non_word)
                    else:
                        _res.append(token.strip())
                else:
                    raise InvalidTokenException("Invalid vocal sounds tag")
            elif len(parts) == 3:
                if parts[1] in VOCAL_CLOSED_CLASS_3:
                    if not word_only:
                        _res.append(f":{parts[0]}:{parts[1]}:")
                    _res.extend(parts[2].split('+'))
                elif parts[1] == 'l':
                    # [2021-08-30 月 16:58] add labelled vocal sounds
                    if BELA_CLASS_LABEL.match(parts[2]):
                        if word_only:
                            _res.append(non_word)
                        else:
                            _res.append(token.strip())
                    else:
                        raise InvalidTokenException("This lablled vocal sound token contains invalid character(s)")
                else:
                    raise InvalidTokenException("invalid unclassifiable vocal sound token")
        elif parts[0] == 'm':
            if mimicked:
                raise InvalidTokenException("Recursive mimicking is not allowed")
            if len(parts) == 2:
                if not word_only:
                    _res.append(":m")
                _res.extend(parts[1].split('+'))  # Mimic(text)
            else:
                _rest = token[token.index(":m")+2:]
                return _process_token(_rest, mimicked=True, non_word=non_word, word_only=word_only, **kwargs)  # mimicked structure
        elif len(parts) == 2:
            if parts[0] == 's':
                if parts[1] in NON_VOCAL_SOUNDS:
                    if word_only:
                        _res.append(non_word,)
                    else:
                        _res.append(f":{parts[0]}:{parts[1]}:")
                else:
                    raise InvalidTokenException("Invalid non vocal sound, closed class token")
            if parts[0] in ('si', "m"):
                if not word_only:
                    _res.append(":" + parts[0])
                _res.extend(parts[1].split("+"))
            if parts[0] == 'd':
                if not word_only:
                    _res.append(":d")
                _res.append(parts[1])
        elif len(parts) == 3:
            if parts[0] == 'l':
                if not word_only:
                    _res.append(":l:" + parts[1])
                _res.extend(parts[2].split('+'))
    elif token.startswith('='):
        if not word_only:
            _res.append("=")
        _res.append(token[1:].strip())
    elif token in ('##', '###'):
        if word_only:
            _res.append(non_word)
        else:
            _res.append(token)
    elif "=" in token:
        _res.extend(token.split("="))
    return _res


def _report_error(message, errors=None):
    if errors is not None:
        errors.append(message)
    else:
        getLogger().warning(message)


INVALID_CHAR = r'\{\}\[\]\r\n\t,ɡʔʲ‘’'
FULLWIDTH_CHARS = r'，。？（）！　'
# [2022-01-06 木 14:05] TA
# Allow ? in Mandarin annotations for now
HALFWIDTH_CHARS = r'\(\)'  # ?
OTHER_LANG_INVALID = re.compile(fr'[{INVALID_CHAR}]')
ENGLISH_INVALID = re.compile(fr'[{INVALID_CHAR}{FULLWIDTH_CHARS}]')
MANDARIN_INVALID = re.compile(fr'[{INVALID_CHAR}{HALFWIDTH_CHARS}]')


def _contain_invalid_characters(text, language=None):
    if not language:
        return OTHER_LANG_INVALID.search(text)
    elif language == 'Mandarin':
        return MANDARIN_INVALID.search(text)
    else:
        return ENGLISH_INVALID.search(text)


def _find_invalid_characters(text, language=None):
    if not language:
        return OTHER_LANG_INVALID.findall(text)
    elif language == 'Mandarin':
        return MANDARIN_INVALID.findall(text)
    else:
        return ENGLISH_INVALID.findall(text)


class TokenList:
    def __init__(self, *args, **kwargs):
        self.__tokens = list(*args, **kwargs)

    def __eq__(self, other):
        return self.__tokens == other

    def __len__(self):
        return len(self.__tokens)

    def __iter__(self):
        return iter(self.__tokens)

    def append(self, token):
        if token is not None:
            # strip off special characters ("=", "~", etc.)
            if token.startswith('='):
                token = token[1:]
            if token.endswith('~'):
                token = token[:-1]
            if token:
                self.__tokens.append(token)

    def extend(self, tokens):
        for t in tokens:
            self.append(t)

    def _append_nlp(self, token, language, nlp_tokenizer=True):
        if nlp_tokenizer:
            self.extend(_nlp_tokenize(token, language=language))
        else:
            self.append(token)

    def _extend_nlp(self, tokens, language, nlp_tokenizer=True):
        for token in tokens:
            self._append_nlp(token, language, nlp_tokenizer=nlp_tokenizer)

    def __repr__(self):
        return f"TokenList({repr(self.__tokens)})"

    def __str__(self):
        return str(self.__tokens)

    def to_list(self):
        return list(self.__tokens)

    def to_tuple(self):
        return tuple(self.__tokens)

    def remove_punc(self):
        self.__tokens = list(_remove_punc(self.__tokens))
        return self


PTN_PRETOKENIZER = re.compile(r'([^ ?　？؟]+|[\?？؟])')


def __pretokenize(text):
    return PTN_PRETOKENIZER.findall(text)


def _nlp_tokenize(text, language='English'):
    if language == 'English' and NLTK_AVAILABLE:
        words = word_tokenize(text)
    elif language == 'Mandarin' and JIEBA_AVAILABLE:
        words = jieba.cut(text, cut_all=False)
    else:
        words = __pretokenize(text)
    return words


def _bela_tokenize(text, non_word=DEFAULT_NON_WORD, errors=None, ellipsis=True,
                   language='English', nlp_tokenizer=True,
                   remove_punc=True, **kwargs):
    ''' Convert MMC convention to normal token text
        >>> process_text(':si:quack+quack+quack+quack+quack tada! :s:clapping finish!')
        >>> 'quack quack quack quack quack tada! XbeepX finish!'
        errors: must be a list, or an object that supports append() function
    '''
    tokens = __pretokenize(text)
    new_tokens = TokenList()
    for token in tokens:
        if is_special_token(token):
            try:
                pieces = _process_token(token, non_word=non_word, **kwargs)
            except InvalidTokenException as e:
                emsg = getattr(e, 'message', str(e))
                _report_error(f"{emsg} ({token})", errors=errors)
                continue
            # except Exception:
            #    pieces = []
            if pieces:
                if ellipsis:
                    _selected = (x for x in pieces if x)
                else:
                    _selected = tuple(x for x in pieces if x and not x.endswith('...'))  # remove ellipsis
                for p in _selected:
                    if p[0] == ':':
                        # do not split special token any further
                        new_tokens.append(p)
                    else:
                        new_tokens._append_nlp(p, language=language, nlp_tokenizer=nlp_tokenizer)
            else:
                _report_error("Invalid token ({})".format(token), errors=errors)
        elif token.endswith('~'):
            new_tokens._append_nlp(token[:-1], language=language, nlp_tokenizer=nlp_tokenizer)
        elif token.startswith("~") or "~" in token:
            _report_error(f"Tildes can only be placed at the end of a token ({token})", errors=errors)
            new_tokens._append_nlp(token, language=language, nlp_tokenizer=nlp_tokenizer)
        elif token.strip() == '...':
            _report_error(f"Ellipsis markers (...) must not follow empty space", errors=errors)
        elif PTN_ELLIPSIS.match(token.strip()):
            _report_error(f"Unknown dots ({token})", errors=errors)
        else:
            # validate ellipsis
            _mi = PTN_INNER_STOP.search(token)
            if _mi:
                _report_error(f"Invalid punctuation ({token})", errors=errors)
            _m = PTN_ELLIPSIS.search(token)
            if _m:
                if len(_m.group(1)) != 3:
                    _report_error(f"Ellipses are denoted by exact 3 full stops ({token} was found)", errors=errors)
                    new_tokens._append_nlp(token, language=language, nlp_tokenizer=nlp_tokenizer)
                elif ellipsis:
                    # this is a valid ellipsis token
                    new_tokens._append_nlp(token[:-3], language=language, nlp_tokenizer=nlp_tokenizer)
            else:
                # normal token
                new_tokens._append_nlp(token, language=language, nlp_tokenizer=nlp_tokenizer)
    return new_tokens.remove_punc() if remove_punc else new_tokens


def process_text(text, non_word=DEFAULT_NON_WORD, errors=None, ellipsis=True, **kwargs):
    ''' Convert MMC convention to normal token text
        >>> process_text(':si:quack+quack+quack+quack+quack tada! :s:clapping finish!')
        >>> 'quack quack quack quack quack tada! XbeepX finish!'
        errors: must be a list, or an object that supports append() function
    '''
    new_tokens = _bela_tokenize(text, non_word=DEFAULT_NON_WORD, errors=errors, ellipsis=ellipsis, **kwargs)
    return " ".join(t.strip() for t in new_tokens)


tokenize = _bela_tokenize


class LanguageMix:
    def __init__(self):
        self.__parts = []  # actual utterance chunks
        self.chunks = []  # collapsed chunks (for language-mix diagram)
        self.length = 0

    def add(self, c):
        ''' Store an utterance chunk '''
        self.__parts.append(c)

    def sort(self):
        self.__parts.sort(key=lambda x: (x.from_ts, x.to_ts))

    def compute(self, auto_sort=True):
        if auto_sort:
            self.sort()
        self.chunks.clear()
        for c in self.__parts:
            # getLogger().debug(f"{c.ID} -- {c.value} [{c.from_ts.value} - {c.to_ts.value}] | {c.language}")
            if self.chunks and self.chunks[-1][0] == c.language:
                self.chunks[-1][1] += c.duration
            else:
                self.chunks.append([c.language, c.duration])
        self.length = sum(x.duration for x in self.__parts)
        return self

    def to_dict(self):
        return {'chunks': self.chunks, 'length': self.length}
