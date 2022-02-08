# -*- coding: utf-8 -*-

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

"""
Lexical Analyser
"""

import logging
from pathlib import Path
from collections import defaultdict as dd
from collections import Counter

from chirptext import chio
from chirptext import ttl

from .common import tokenize
from .common import NLTK_AVAILABLE
from .common import _process_token, InvalidTokenException


def read_lexicon(lex_name):
    p = Path(__file__).parent / 'data' / lex_name
    forms = set()
    with chio.open(p) as _lex_stream:
        for line in _lex_stream:
            if line.startswith("#"):
                continue
            else:
                forms.add(line.strip())
    return forms


# TODO add all BELA special keywords
_KEYWORDS = ['babyname', 'adultname', 'siblingname', 'strangername',
             '...', 'english', 'chinese', 'malay', 'tamil']
if NLTK_AVAILABLE:
    from nltk.corpus import words  # English words
    from nltk.corpus import stopwords
    _ENGLISH_WORDS = set(words.words())
    _ENGLISH_WORDS.update(stopwords.words('english'))
else:
    _ENGLISH_WORDS = set()
_ENGLISH_WORDS.update(("'s", "ok", "'m", "'ll", "n't", "okay", "'re", "'d", "'ve"))
_MANDARIN_WORDS = read_lexicon('cmn_lex.txt.gz')
_MALAY_WORDS = read_lexicon('msa_lex.txt.gz')


# [2021-03-11 木 11:48]
# Adopted from https://github.com/letuananh/lelesk/blob/master/lelesk/util.py
# LeLESK: MIT License
if NLTK_AVAILABLE:
    # from nltk.tokenize import word_tokenize
    from nltk import pos_tag
    from nltk.stem import WordNetLemmatizer

    wnl = WordNetLemmatizer()


def ptpos_to_wn(ptpos, default='x'):
    ''' Penn Treebank Project POS to WN '''
    if ptpos.startswith('JJ'):
        return 'a'
    elif ptpos.startswith('NN'):
        return 'n'
    elif ptpos.startswith('RB'):
        return 'r'
    elif ptpos.startswith('VB'):
        return 'v'
    else:
        return default


def _tokenize(words):
    if NLTK_AVAILABLE:
        tags = pos_tag(words)
        tokens = [(w, t, wnl.lemmatize(w, pos=ptpos_to_wn(t, default='n'))) for w, t in tags]
        return tokens
    else:
        return words


class LexicalAnalyser:
    def __init__(self, lang_lex_map=None, word_only=False, ellipsis=False, non_word='', lemmatizer=True, **kwargs):
        self.utterances = ttl.Document()
        self.word_sent_map = dd(set)
        self.lang_word_sent_map = dd(lambda: dd(set))
        self.lang_word_speaker_map = dd(lambda: dd(set))
        self.word_only = word_only
        self.ellipsis = ellipsis
        self.non_word = non_word
        self.lemmatizer = lemmatizer
        # setup built-in language-lexicon map
        self.lang_lex_map = {
            'English': _ENGLISH_WORDS,
            'Mandarin': _MANDARIN_WORDS,
            'Malay': _MALAY_WORDS
        }
        # allow custom language_map
        self.__custom_lang_lex_map = lang_lex_map if lang_lex_map else {}
        self.word_speaker_map = dd(set)
        self.word_map = dd(Counter)

    def analyse(self, external_tokenizer=True):
        self.word_sent_map.clear()
        self.word_map.clear()
        for utterance in self.utterances:
            language = utterance.tag.language.value
            speaker = utterance.tag.speaker.value
            # source = utterance.tag.source.value
            tokens = [t.lower() for t in tokenize(
                utterance.text, language=language,
                ellipsis=self.ellipsis, non_word=self.non_word,
                word_only=self.word_only, nlp_tokenizer=external_tokenizer)]
            self.word_map[language].update(tokens)
            for token in tokens:
                self.word_speaker_map[token] = speaker
                self.word_sent_map[token].add(utterance.text)
                self.lang_word_speaker_map[language][token].add(speaker)
                self.lang_word_sent_map[language][token].add(utterance.text)

    def gen_type_token_map(self):
        ratio_map = {}
        for lang, counter in self.word_map.items():
            count_token = len(list(counter.elements()))
            count_type = len(counter)
            ratio = count_token / count_type if count_type > 0 else 0
            ratio_map[lang] = (count_token, count_type, ratio)
        return ratio_map

    def gen_type_token_list(self):
        _list = [(lang, count_token, count_type, ratio) for lang, (count_token, count_type, ratio) in self.gen_type_token_map().items()]
        _list.sort(key=lambda x: -x[3])
        return _list

    def add(self, text, language, **kwargs):
        sent = self.utterances.sents.new(text)
        sent.tag.language = language
        for k, v in kwargs.items():
            sent.tag[k] = v

    def is_special_token(self, word, language):
        ''' Determine if a given token is a special token (keywords, markup, etc.) '''
        return word == '###' or word.startswith(':')

    def is_unknown(self, word, language):
        '''Check if a word is a known word (exists in the current lexicon)'''
        if word in _KEYWORDS:
            return False
        elif language in self.lang_lex_map:
            if word in self.lang_lex_map[language]:
                return False
            elif language not in self.__custom_lang_lex_map:
                return True
            else:
                return word not in self.__custom_lang_lex_map[language]
        elif language in self.__custom_lang_lex_map:
            return word not in self.__custom_lang_lex_map[language]
        else:
            return False

    def to_dict(self, ignore_empty=True):
        stats_dict = {'languages': [], 'lexicon': [], 'errors': []}
        __lemmatize_error = False
        for lang, count_token, count_type, ratio in self.gen_type_token_list():
            if ignore_empty and not count_type and not count_token and not ratio:
                continue
            stats_dict['languages'].append({
                'language': lang,
                'types': count_type,
                'tokens': count_token,
                'ratio': round(ratio, 2)
            })
        for lang, counter in self.word_map.items():
            lang_lexicon = {'language': lang, 'vocabs': []}
            for word, freq in counter.most_common():
                _is_special = self.is_special_token(word, lang)
                if _is_special:
                    try:
                        _process_token(word)
                        _is_unknown = False
                    except InvalidTokenException:
                        _is_unknown = True
                else:
                    lemma = word
                    # try to lemmatize if possible
                    if NLTK_AVAILABLE and self.lemmatizer and not __lemmatize_error and lang == 'English':
                        try:
                            __, tag = pos_tag([word])[0]
                            lemma = wnl.lemmatize(word, pos=ptpos_to_wn(tag, default='n'))
                        except Exception as e:
                            # logging.getLogger(__name__).exception("BELA.Lemmatizer crashed")
                            # do not lemmatize if NLTK crashed
                            __lemmatize_error = True
                            if isinstance(e, LookupError):
                                if 'omw-1.4' in str(e):
                                    stats_dict['errors'].append(f'Lexicon was generated without lemmatizer. OMW-1.4 data not found.')
                                else:
                                    stats_dict['errors'].append(f'Lexicon was generated without lemmatizer. Unknown resource missing.')
                            else:
                                stats_dict['errors'].append('Lexicon was generated without lemmatizer. Unknown error was raised.')
                    _is_unknown = self.is_unknown(lemma, lang)
                _lex_entry = {
                    'word': word,
                    'freq': freq,
                    'sents': list(self.lang_word_sent_map[lang][word]),
                    'speakers': list(self.lang_word_speaker_map[lang][word]),
                    'special_code': _is_special,
                    'unknown_word': _is_unknown
                }
                lang_lexicon['vocabs'].append(_lex_entry)
            if not ignore_empty or lang_lexicon['vocabs']:
                stats_dict['lexicon'].append(lang_lexicon)
        return stats_dict


class CorpusLexicalAnalyser:
    ''' Analyse a corpus text '''
    def __init__(self, filepath=':memory:', lang_lex_map=None, word_only=False, lemmatizer=True, **kwargs):
        self.filepath = filepath
        self.word_only = word_only
        self.lemmatizer = lemmatizer
        self.__lang_lex_map = {} if lang_lex_map is None else lang_lex_map
        self.profiles = dd(self._create_lex_analyzer)

    def _create_lex_analyzer(self):
        return LexicalAnalyser(lang_lex_map=self.__lang_lex_map,
                               word_only=self.word_only,
                               lemmatizer=self.lemmatizer)

    def read(self, **kwargs):
        ''' Read the CSV file content specified by self.filepath '''
        for text, language, source, speaker in chio.read_csv_iter(self.filepath, **kwargs):
            self.add(text, language, source=source, speaker=speaker)
        return self

    def add(self, text, language, source='', speaker=''):
        if text is None:
            text = ''
        if language is None:
            language = ''
        if source is None:
            source = ''
        if speaker is None:
            speaker = ''
        self.profiles['ALL'].add(text, language, source=source, speaker=speaker)
        self.profiles[speaker].add(text, language, source=source, speaker=speaker)

    def analyse(self, external_tokenizer=True):
        ''' Analyse all available profiles (i.e. speakers) '''
        for profile in self.profiles.values():
            profile.analyse(external_tokenizer=external_tokenizer)
        return self

    def to_dict(self):
        ''' Export analysed result as a JSON-ready object '''
        profile_list = []
        for pname in sorted(self.profiles.keys()):
            profile = self.profiles[pname]
            profile_list.append({
                'name': pname,
                'stats': profile.to_dict()
            })
        return profile_list
