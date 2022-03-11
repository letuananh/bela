# -*- coding: utf-8 -*-

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

"""
BELA version 1.x convention
"""

from collections import defaultdict as dd
from collections import OrderedDict

from chirptext import chio
from chirptext.anhxa import DataObject
from speach.ttlig import IGRow
from speach.elan import parse_eaf_stream
from speach.vtt import sec2ts

from .common import TIER_PARSER
from .common import UTTERANCE_GAP_THRESHOLD
from .common import KNOWN_LANGUAGES
from .common import LanguageMix


class Transcript(DataObject):
    """
    Represent a transcript of a recording, mainly constructed from CSV data)
    """

    def __init__(self):
        self.__sents = []  # utterances sorted by starting time
        self.__tiers = dd(list)

    def insert(self, text, tsfrom, tsto=None, tsduration=None, tier=None, **kwargs):
        ''' Add an annotation chunk to a tier '''
        ig = IGRow(text=text, tsfrom=float(tsfrom), **kwargs)
        if tsto is not None:
            ig.tsto = float(tsto)
            if tsduration is not None:
                expected = round(ig.tsduration, 3)
                if expected != round(float(tsduration), 3):
                    raise ValueError("Inconsistent values for tsfrom ({}), tsto ({}), and tsduration ({}). Expected tsduration=({})".format(tsfrom, tsto, tsduration, expected))
        elif tsduration is not None:
            ig.tsto = ig.tsfrom + float(tsduration)
        if tier is not None:
            ig.tier = tier
        self.__tiers[ig.tier].append(ig)
        self.__sents.append(ig)

    def tier_names(self):
        return tuple(self.__tiers.keys())

    def tier(self, tier_name):
        return self.__tiers[tier_name] if tier_name in self.__tiers else None

    def __len__(self):
        return len(self.__sents)

    def __getitem__(self, idx):
        return self.__sents[idx]

    def sort(self):
        ''' Sort all utterances '''
        self.__sents.sort(key=lambda sent: (sent.tsfrom, sent.tsto))
        for tier in self.__tiers.values():
            tier.sort(key=lambda sent: (sent.tsfrom, sent.tsto))
        return self.__sents

    def tag_language(self, utterance_tier_name, language_tier_name, default_value=''):
        ''' Use text value from language_tier as language to tag utterances
            default_value -- Default language value (defaulted to an empty string)
        '''
        utterance_tier = self.__tiers[utterance_tier_name]
        language_tier = self.__tiers[language_tier_name]
        for u in utterance_tier:
            candidates = []
            for l in language_tier:
                score = u.overlap(l)
                if score > 0:
                    candidates.append((score, l))
                if l.tsfrom > u.tsto:
                    break
            if candidates:
                u.language = max(candidates, key=lambda x: x[0])[1].text.strip()  # .replace(':', '__')
            elif not u.language:
                u.language = default_value
        return utterance_tier

    def join_utterances(self, tier_name=None, tier_class=None):
        ''' Group adjecent utterances together. Return a list of joined utterance lists '''
        _timeline = self.__sents if tier_name is None else self.__tiers[tier_name]
        _utterances = []
        _current = []  # current group
        for idx, s in enumerate(_timeline):
            if tier_class and s.tier_class != tier_class:
                continue
            if idx == 0:
                _current.append(s)
            elif s.speaker == _timeline[idx - 1].speaker and abs(s.tsfrom - _timeline[idx - 1].tsto) < UTTERANCE_GAP_THRESHOLD:
                _current.append(s)
            else:
                # flush
                if _current:
                    _utterances.append(_current)
                _current = [s]
        if _current:
            _utterances.append(_current)
        return _utterances

    @staticmethod
    def from_rows(rows):
        ''' create a Transcript object from CSV rows (list of list) '''
        transcript = Transcript()
        for row in rows:
            if len(row) == 5:
                tier, start_sec, end_sec, dur_sec, text = row
                transcript.insert(text, start_sec, tsto=end_sec, tsduration=dur_sec, tier=tier)
            elif len(row) == 6:
                tier, speaker, start_sec, end_sec, dur_sec, text = row
                transcript.insert(text, start_sec, tsto=end_sec, tsduration=dur_sec, tier=tier, speaker=speaker)
            else:
                getLogger().warning(f"Invalid line {row}")
                continue
        return transcript

    @staticmethod
    def read_tsv(file_path, *args, **kwargs):
        return Transcript.from_rows(chio.read_tsv_iter(file_path, *args, **kwargs))


class Bela1:
    ''' This class represent BELA convention version 1'''

    def __init__(self):
        """
        All information about an ELAN transcript
        """
        self.persons = set()  # all persons in this transcript
        self.person_code_map = dd(set)  # a list of all associated codes of this person
        self.person_duration = dd(float)
        self.person_languages = dd(lambda: dd(float))
        self.person_utterances = dd(list)
        self.language_duration = dd(float)
        self.person_warnings = dd(set)
        self.tiers = set()    # all tiers in this transcript
        self.person_tiers = dd(set)
        self.weird_names = set()  # detect weird tier names

        self.tokens = set()
        self.words = set()
        self.languages = set()
        self.others = set()
        self.sents = []
        self.csw = None  # all CSV rows as IGRow
        self.filepath = None

    def sorted_person_tiers(self):
        d = dict()
        for k in sorted(self.person_tiers.keys()):
            d[k] = sorted(self.person_tiers[k])
        # print(d)
        return d

    def code_person_map(self):
        cp_map = OrderedDict()
        for p, codes in self.person_code_map.items():
            for c in codes:
                if c in cp_map:
                    raise Exception(f"Duplicated code {c} for person {p} -- All: {codes}")
                else:
                    cp_map[c] = p
        return cp_map

    def sort_languages(self, languages=None):
        if languages is None:
            languages = self.languages
        return sorted(languages, key=lambda i: (i not in KNOWN_LANGUAGES, i != 'Red Dot', i))

    def to_dict(self):
        people = []
        for person in sorted(self.persons):
            person_languages = [(lang, round(duration, 2)) for lang, duration in self.person_languages[person].items()]
            person_languages.sort(key=lambda x: x[1])
            person_languages.reverse()
            person_dict = {'name': person,
                           'code': list(self.person_code_map[person]),
                           'duration': round(self.person_duration[person], 2),
                           'languages': person_languages,
                           'tiers': list(self.person_tiers[person]),
                           'utterance_count': len(self.person_utterances[person])}
            people.append(person_dict)
        return {
            'languages': [(l, round(self.language_duration[l], 2)) for l in self.sort_languages()],
            'people': people
        }

    def to_language_mix(self, to_ts=None, auto_compute=True):
        ''' Collapse utterances to generate a language mix timeline '''
        langmix = LanguageMix()
        for _person_name, _utterances in self.person_utterances.items():
            for u in _utterances:
                if u.chunks is not None:
                    for c in u.chunks:
                        if c.tsfrom and c.tsto:
                            if to_ts is not None and c.tsto > to_ts:
                                continue
                            else:
                                # getLogger().debug(f"{c.ID} -- {c.value} [{c.from_ts.value} - {c.to_ts.value}] | {c.language}")
                                c.duration = c.tsduration
                                langmix.add(c)
                elif u.tsfrom and u.tsto:
                    u.duration = u.tsduration
                    langmix.add(u)
                else:
                    print(f"Ignoring {u}")
        return langmix.compute() if auto_compute else langmix

    @staticmethod
    def read(filepath, autotag=True):
        ''' Read ELAN csv file '''
        _transcript = Bela1()
        _transcript.filepath = filepath
        _transcript.csw = Transcript.read_tsv(filepath)
        return Bela1.process_transcript(_transcript, autotag=autotag)

    @staticmethod
    def read_eaf(eaf_path):
        elan = parse_eaf_stream(eaf_path)
        return Bela1.from_elan(elan, eaf_path)

    @staticmethod
    def from_elan(elan, eaf_path=":memory:"):
        elanplus = Bela1.parse_rows(elan.to_csv_rows(), filepath=eaf_path)
        elanplus.elan = elan  # store pointer to ELAN object
        return elanplus

    @staticmethod
    def parse_rows(rows, autotag=True, filepath=':memory:'):
        _transcript = Bela1()
        _transcript.filepath = filepath
        _transcript.csw = Transcript.from_rows(rows)
        return Bela1.process_transcript(_transcript, autotag=autotag)

    @staticmethod
    def process_transcript(_transcript, autotag=True):
        for name in _transcript.csw.tier_names():
            m = TIER_PARSER.match(name)
            if m:
                person = m.group('person')
                tier = m.group('tier')
                _transcript.persons.add(person)
                _transcript.tiers.add(tier)
            elif name in ("ActivityMarkers"):
                pass
            else:
                _transcript.weird_names.add(name)
        # auto tag languages
        if autotag:
            tier_names = _transcript.csw.tier_names()
            for person in _transcript.persons:
                utterance_tier = "{} (Utterance)".format(person)
                language_tier = "{} (Language)".format(person)
                if utterance_tier in tier_names and language_tier in tier_names:
                    _transcript.csw.tag_language(utterance_tier, language_tier, "#!#?")
        # extract corpus
        for sent in _transcript.csw:
            m = TIER_PARSER.match(sent.tier)
            _person_name = None
            tsduration = sent.tsduration
            if m:
                _person_name = m.group('person')
                sent.speaker_name = _person_name
                _transcript.person_tiers[_person_name].add(m.group('tier'))
                sent.tier_class = m.group('tier')
                if sent.speaker:
                    _transcript.person_code_map[m.group('person')].add(sent.speaker)
            if sent.tier == 'Transcriber (Comment)':
                # ignore all Transcriber comment
                continue
            if sent.tsduration < 0:
                print("WARNING: invalid utterance: {} ({}) From: {} - To: {}".format(sent.text, sent.tsduration, sec2ts(sent.tsfrom), sec2ts(sent.tsto)))
                _transcript.person_warnings[_person_name].add('Negative utterances ({:.2f})'.format(sent.tsduration))
                tsduration = 0
            if sent.text.strip() == '':
                warn_text = "Blank: {} [{} -- {}]".format(_person_name, sec2ts(sent.tsfrom), sec2ts(sent.tsto))
                _transcript.person_warnings[_person_name].add(warn_text)
            if sent.tier_class in ('Utterance', 'Comment'):
                if _person_name and sent.tsduration:
                    _transcript.person_duration[_person_name] += tsduration
                    _transcript.person_utterances[_person_name].append(sent)
                if sent.language in ('', '#!#?'):
                    warn_text = "language???: {} [{} -- {}] {}".format(_person_name, sec2ts(sent.tsfrom), sec2ts(sent.tsto), sent.text)
                    print(warn_text)
                    _transcript.person_warnings[_person_name].add(warn_text)

                txt = sent.text.strip()
                _transcript.sents.append(txt)
                _tks = [x.strip() for x in txt.split()]
                _transcript.tokens.update(_tks)
                _transcript.words.update(_tks)
            elif sent.tier_class == 'Language':
                lng = sent.text.strip()
                _transcript.tokens.update((lng,))
                _transcript.languages.update((lng,))
                _transcript.language_duration[lng] += tsduration
                if _person_name:
                    _transcript.person_languages[_person_name][lng] += tsduration
            else:
                _transcript.tokens.update(_tks)
                _transcript.others.update(_tks)
        if _transcript.person_warnings:
            print(_transcript.person_warnings)
        return _transcript


def build_utterances_json(elanplus):
    ''' Extract all utterances from an Bela1 object, join them by tier_class "Utterance"
    and then return a JSON-ready dictionary '''
    sents = []
    for us in elanplus.csw.join_utterances(tier_class="Utterance"):
        utterances = []
        for u in us:
            utterances.append({k: v for k, v in u.to_dict().items() if v != ""})
        sents.append(utterances)
    return sents
