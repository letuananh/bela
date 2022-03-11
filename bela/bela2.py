# -*- coding: utf-8 -*-

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

"""
BELA version 2.x convention
"""

import logging
from collections import deque
from chirptext import DataObject
from speach import elan

from .common import TIER_PARSER
from .common import tokenize
from .common import LanguageMix
from .common import _find_invalid_characters


def getLogger():
    return logging.getLogger(__name__)


SPECIAL_TIERS = ['ActivityMarkers']
SPECIAL_SPEAKER_NAME = 'Transcriber'
SPECIAL_SPEAKER = ':transcriber:'
DEFAULT_TURN_THRESHOLD = 1500


def parse_tier_name(name):
    ''' Parse BELA tier name convention '''
    m = TIER_PARSER.match(name)
    if m:
        return m.group('person'), m.group('tier')
    else:
        return None, None


def time_map(tier):
    _time_map = {}
    for u in tier:
        _time_map[(u.from_ts, u.to_ts)] = u
        if u.from_ts is not None and u.from_ts.value is not None \
           and u.to_ts is not None and u.to_ts.value is not None:
            _time_map[(u.from_ts.value, u.to_ts.value)] = u
    return _time_map


def _map_children(parent_tier, child_tier, errors=None, tier_class='chunks', is_many=True):
    ''' map all children chunks into parent's utterances '''
    _parents = sorted(parent_tier, key=lambda x: x.from_ts)
    _children = deque(sorted(child_tier, key=lambda x: x.from_ts))
    for ann in _parents:
        while _children:
            ann_child = _children[0]
            if ann_child.from_ts >= ann.from_ts and ann_child.to_ts <= ann.to_ts:
                if is_many:
                    if not getattr(ann, tier_class):
                        setattr(ann, tier_class, [])
                    getattr(ann, tier_class).append(ann_child)
                else:
                    if getattr(ann, tier_class) is None:
                        setattr(ann, tier_class, ann_child)
                    else:
                        getLogger().warning("Conflicting child annotations were found")
                        if errors is not None:
                            errors.append("Conflicting child annotations were found")
                _children.popleft()
                getLogger().debug(f"linked: {repr(ann)} -- {repr(ann_child)}")
            elif ann.from_ts > ann_child.to_ts:
                getLogger().warning(f"DISCARDED -- {repr(ann_child)}")
                if errors is not None:
                    errors.append(f"Orphaned annotation found -- (#{ann_child.ID}) {repr(ann_child)}")
                _children.popleft()
            else:
                getLogger().debug(f"no relation: {repr(ann)} -- {repr(ann_child)}")
                break
    if _children:
        for child in _children:
            getLogger().debug(f"Orphaned annotation found: {child}")

class Person(DataObject):
    def __init__(self, name, code=None, utterances=None, tiers=[], belav2=None, **kwargs):
        super().__init__(name=name, code=code, utterances=utterances, **kwargs)
        self.belav2 = belav2
        self.__tier_map = {}
        self.__tiers = list(tiers) if tiers else []

    @property
    def tiers(self):
        return self.__tiers

    @property
    def tier_classes(self):
        return list(self.__tier_map.keys())

    def __contains__(self, key):
        return key in self.__tier_map

    def __getitem__(self, key):
        return self.__tier_map[key] if key in self.__tier_map else None

    def __iter__(self):
        return iter(self.tiers)

    def add_tier(self, tier):
        if tier in self.tiers:
            return
        if not tier.tier_class:
            if self.belav2 is not None:
                self.belav2.errors.append(f"Tier [{tier.ID}] does not have a tier_class")
            else:
                getLogger().warning(f"Tier [{tier.ID}] does not have a tier_class")
        elif tier.tier_class in self.__tier_map:
            if self.belav2 is not None:
                self.belav2.errors.append(f"User [{self.code}] has more than one [class={tier.tier_class}] tier")
            else:
                getLogger().warning(f"User [{self.code}] has more than one [class={tier.tier_class}] tier")
        else:
            self.__tier_map[tier.tier_class] = tier
        self.tiers.append(tier)

    def __str__(self):
        return f"Person(name={repr(self.name)}, code={repr(self.code)})"


class Bela2(DataObject):
    ''' BELA-convention version 2
    '''

    def __init__(self, elan, path=":memory:", allow_empty=False,
                 nlp_tokenizer=False, word_only=True, ellipsis=True,
                 split_punc=True, remove_punc=True, **kwargs):
        ''' Create a new Bela2 object from an :class:`speach.elan.ELANDoc` object

        :param: elan: An ELANDoc object
        :type: elan: speach.elan.ELANDoc

        :returns: a Bela2 object
        :rtype: bela.Bela2
        '''
        super().__init__(elan=elan, path=path, errors=[], warnings=[],
                         allow_empty=allow_empty, **kwargs)
        self.__person_map = {}
        # create special speaker map (i.e. Transcriber)
        self.__person_map[SPECIAL_SPEAKER] = Person(name=SPECIAL_SPEAKER_NAME, code=SPECIAL_SPEAKER, belav2=self)
        self.__persons = None
        self.__participant_codes = None
        self.__word_only = word_only
        self.__nlp_tokenizer = nlp_tokenizer
        self.__ellipsis = ellipsis
        self.__split_punc = split_punc
        self.__remove_punc = remove_punc
        if elan is not None:
            self.parse_names()
            self._init_tier_map()
            self.tokenize()

    def tiers(self):
        return self.elan.tiers()

    @property
    def roots(self):
        ''' Direct access to all underlying ELAN root tiers '''
        return self.elan.roots

    @property
    def person_map(self):
        ''' Map participant (i.e. person code) to person object '''
        return self.__person_map

    @property
    def persons(self):
        ''' All Person objects in this BELA object '''
        if self.__persons is None:
            self.__persons = tuple(self.__person_map.values())
        return self.__persons

    @property
    def participant_codes(self):
        ''' Immutable list of participant codes '''
        if self.__participant_codes is None:
            # TODO: Make this thread safe?
            self.__participant_codes = tuple(i for i in self.person_map.keys())
        return self.__participant_code

    @property
    def word_only(self):
        return self.__word_only

    def count_sents(self):
        utt_count = 0
        for tier in self.elan:
            if tier.tier_class == "Utterance":
                utt_count += len(tier)
        return utt_count

    def count_chunks(self):
        chunk_count = 0
        for tier in self.elan:
            if tier.tier_class == "Chunk":
                chunk_count += len(tier)
        return chunk_count

    def get_language_set(self):
        languages = set()
        for tier in self.elan:
            if tier.tier_class == "Language":
                for ann in tier:
                    languages.add(ann.value)
        return set(languages)

    def parse_name(self, tier):
        ''' (Internal) Parse participant name and tier type from a tier object and then update the tier object

        This function is internal and should not be used outside of this class.

        :param tier: The tier object to parse
        :type tier: speach.elan.ELANTier
        '''

        if tier.ID in SPECIAL_TIERS:
            tier.tier_class = tier.ID
            tier.speaker_name = SPECIAL_SPEAKER
        else:
            speaker_name, tier_class = parse_tier_name(tier.ID)
            if speaker_name and tier_class:
                tier.tier_class = tier_class
                tier.speaker_name = speaker_name
            else:
                self.errors.append(f"Invalid tier name: {tier.ID}")

    def _init_tier_map(self):
        ''' Construct BELA info structure from EAF '''
        # init roots first
        for tier in self.roots:
            if tier.tier_class == 'Utterance':
                if not tier.participant:
                    self.errors.append(f"Tier [{tier.ID}] does not have participant code")
                elif tier.participant in self.__person_map:
                    self.errors.append(f"Person [{tier.participant}] has more than one utterance tier")
                else:
                    person = Person(tier.speaker_name, code=tier.participant, utterances=tier, belav2=self)
                    self.__person_map[tier.participant] = person
            elif tier.ID not in SPECIAL_TIERS:
                self.errors.append(f"Unknown root tier: {tier.ID}")
        # init other tiers
        for tier in self.elan:
            # verify timestamps
            if tier.time_alignable:
                for ann in tier:
                    if ann.from_ts is None or ann.from_ts.value is None or ann.to_ts is None or ann.to_ts.value is None:
                        self.errors.append(f"Annotation with corrupted timestamp: {ann.value} (Timestamp: {ann.from_ts} -- {ann.to_ts}) | Tier: {tier.ID}")
                        if ann.errors is None:
                            ann.errors = []
                        ann.errors.append(f"Corrupted timestamp: {ann.value} | (Timestamp: {ann.from_ts} -- {ann.to_ts})")
                        if ann.from_ts is not None or (ann.from_ts.value is None and ann.to_ts is not None):
                            ann.from_ts.value = ann.to_ts.value
                            ann.errors.append("Assumed from_ts value from to_ts")
                        if ann.to_ts is not None and ann.to_ts.value is None and ann.from_ts is not None:
                            ann.to_ts.value = ann.from_ts.value
                            ann.errors.append("Assumed to_ts value from from_ts")
            if tier.ID in SPECIAL_TIERS:
                self.__person_map[SPECIAL_SPEAKER].tiers.append(tier)
            elif tier.participant not in self.__person_map:
                self.errors.append(f"Unknown person code [{tier.participant}] used in tier [{tier.ID}]")
            else:
                self.__person_map[tier.participant].add_tier(tier)
        # link languages if available
        for person in self.persons:
            if person.utterances:
                for u in person.utterances:
                    u.person = person
                if person['Chunk']:
                    _map_children(person.utterances, person['Chunk'], errors=self.errors, tier_class='chunks')
                else:
                    self.errors.append(f"Person {person.name} ({person.code}) does not have a chunk tier")
                if not person['Language']:
                    self.errors.append(f"Person {person.name} ({person.code}) does not have a language tier")
                if 'Translation' in person:
                    translations = person['Translation']
                    _translation_map = {u.ref: u.value for u in translations}
                    for u in person.utterances:
                        if u in _translation_map:
                            if not u.translation:
                                u.translation = _translation_map[u]
                            else:
                                self.errors.append(f"Conflicted translation for [{person}] Time: [{u.from_ts} -- {u.to_ts}]")
                else:
                    self.errors.append(f"Person {person.name} ({person.code}) does not have a translation tier")
            if person['Chunk'] and person['Language']:
                lang_tier_time_map = time_map(person['Language'])
                linked_language_annotations = set(person['Language'])
                for cu in person['Chunk']:
                    key = (cu.from_ts, cu.to_ts)
                    if key in lang_tier_time_map:
                        cu.language = lang_tier_time_map[key].value
                        linked_language_annotations.remove(lang_tier_time_map[key])
                    elif cu.from_ts is not None and cu.from_ts.value is not None \
                         and cu.to_ts is not None and cu.to_ts.value is not None:
                        # [2021-09-07 火 14:32]
                        # [TA] try to map using timestamp values if possible
                        key = (cu.from_ts.value, cu.to_ts.value)
                        if key in lang_tier_time_map:
                            cu.language = lang_tier_time_map[key].value
                            linked_language_annotations.remove(lang_tier_time_map[key])
                if linked_language_annotations:
                    for ann in linked_language_annotations:
                        self.errors.append(f"Orphaned language annotation could not be linked: {ann} [{ann.from_ts} -- {ann.to_ts}]")
            # validate text from utterance tier and chunk tier
            if person.utterances:
                for u in person.utterances:
                    if u.errors is None:
                        u.errors = []
                    if u.warnings is None:
                        u.warnings = []
                    if not u.text.strip():
                        if not self.allow_empty:
                            u.errors.append(f"Empty annotation '' found at [{u.from_ts} :: {u.to_ts}]")
                        else:
                            u.warnings.append(f"Empty annotation '' found at [{u.from_ts} :: {u.to_ts}]")
                    if u.chunks:
                        for cu in u.chunks:
                            if not cu.text.strip():
                                if u.text or not self.allow_empty:
                                    u.errors.append(f"Empty chunk annotation '' found at [{cu.from_ts} :: {cu.to_ts}]")
                                else:
                                    u.warnings.append(f"Empty chunk annotation '' found at [{cu.from_ts} :: {cu.to_ts}]")
                            if cu.language is None or not cu.language.strip():
                                if not self.allow_empty or cu.text.strip() or u.text.strip():
                                    u.errors.append(f"Language tag not found in the chunk `{cu.text.strip()}` [{cu.from_ts} :: {cu.to_ts}]")
                                else:
                                    u.warnings.append(f"Language tag not found in the chunk `{cu.text.strip()}` [{cu.from_ts} :: {cu.to_ts}]")
                            elif "#!" in cu.language:
                                u.errors.append(f"Unsure language tag ({cu.language}) was used for chunk `{cu.text.strip()}` [{cu.from_ts} :: {cu.to_ts}]")
                    u_value = u.text.replace(' ', '')
                    _chunks = u.chunks if u.chunks else []
                    c_value = ''.join(x.text for x in _chunks)
                    c_value = c_value.replace(' ', '')
                    if u_value != c_value:
                        _chunk_texts = ' '.join(x.text.strip() for x in _chunks)
                        # logging.getLogger(__name__).info(f"mismatch:\n   + u_value: {repr(u_value)}\n   + c_value: {repr(c_value)}")
                        u.errors.append(f"Utterance text and chunks are mismatched ({repr(u.text)} != {repr(_chunk_texts)})")

    def parse_names(self):
        for tier in self.elan:
            self.parse_name(tier)

    def tokenize(self):
        ''' tokenize all utterances '''
        for tier in self.elan:
            if tier.tier_class in ('Utterance', 'Chunk'):
                for ann in tier:
                    ann_errors = [] if ann.errors is None else ann.errors
                    ann.words = tokenize(ann.value, language=ann.language,
                                         errors=ann_errors,
                                         ellipsis=self.__ellipsis,
                                         nlp_tokenizer=self.__nlp_tokenizer,
                                         split_punc=self.__split_punc,
                                         remove_punc=self.__remove_punc,
                                         word_only=self.__word_only)
                    _invalid_chars = _find_invalid_characters(ann.value, language=ann.language)
                    if _invalid_chars:
                        if ann.language:
                            ann_errors.append(f"Invalid characters, new line, or tab found ({repr(_invalid_chars)}) (language: {ann.language})")
                        else:
                            ann_errors.append(f"Invalid characters, new line, or tab found ({repr(_invalid_chars)})")
                    ann.errors = ann_errors
                pass

    def find_turns(self, threshold=DEFAULT_TURN_THRESHOLD):
        ''' Find potential turn-takings

        :param threshold: Delay between utterances in milliseconds
        :type threshold: float

        :return: List of utterance pairs (2-tuple) (from utterance, to utterance object)
        '''
        _utterances = []
        for person_code, person in self.person_map.items():
            if person.utterances:
                for u in person.utterances:
                    u.person = person
                    _utterances.append(u)
        _utterances.sort(key=lambda x: x.from_ts)
        # is_turn = False
        _turns = []
        for idx, u in enumerate(_utterances):
            if idx == len(_utterances) - 1:
                continue
            next_u = _utterances[idx + 1]
            if u.to_ts is None or u.to_ts.value is None or \
               next_u.from_ts is None or next_u.from_ts.value is None:
                continue
            delta_t = u.to_ts - next_u.from_ts
            if next_u.person != u.person and abs(delta_t) <= threshold:
                _turns.append((u, next_u))
                # is_turn = True
        return _turns

    def to_language_mix(self, to_ts=None, auto_compute=True):
        ''' Collapse utterances to generate a language mix timeline '''
        langmix = LanguageMix()
        for person in self.persons:
            if not person.utterances:
                continue
            getLogger().debug(f"{person.name}  -- {person.code}")
            for u in person.utterances:
                if u.chunks:
                    for c in u.chunks:
                        if c.from_ts and c.to_ts:
                            if to_ts is not None and c.to_ts > to_ts:
                                continue
                            else:
                                langmix.add(c)
        return langmix.compute() if auto_compute else langmix

    @staticmethod
    def read_eaf(eaf_path, **kwargs):
        ''' Read an EAF file as a Bela2 object

        :param eaf_path: Path to the EAF file
        :type eaf_path: str-like object or a Path object
        :returns: A Bela2 object
        :rtype: bela.Bela2
        '''
        return Bela2(elan.read_eaf(eaf_path), path=eaf_path, **kwargs)

    @staticmethod
    def from_elan(elan, eaf_path=":memory:", **kwargs):
        ''' Create a BELA-con version 2.x object from a :class:`speach.elan.ELANDoc` object '''
        return Bela2(elan, path=eaf_path, **kwargs)
