# -*- coding: utf-8 -*-

# This code is a part of BELA package: https://github.com/letuananh/bela
# :developer: Le Tuan Anh <tuananh.ke@gmail.com>
# :license: MIT, see LICENSE for more details.

from pathlib import Path
from speach import elan
from .bela2 import Bela2

"""
BELA transcription builder
"""

_TEMPLATE_PATH = Path(__file__).parent / 'data' / 'bela_v3_blank.eaf'


def _create_blank_bela():
    return elan.read_eaf(_TEMPLATE_PATH)


class Builder:
    """ BELA transcript builder
    """

    def __init__(self, add_marker=False, *args, **kwargs):
        """ Return a blank BELA2 transcript builder object
        """
        self.eaf = _create_blank_bela()
        if add_marker:
            self.add_marker()

    def add_marker(self):
        self.eaf.new_tier('ActivityMarkers', 'Activity_Marker')

    def create_participant(self, name, participant='', target=True, matrix=True, sensitive=True):
        ''' Create tier structure for a new participant '''
        self.eaf.new_tier(f'{name} (Utterance)', 'Utterance', participant=participant)
        self.eaf.new_tier(f'{name} (Chunk)', 'Chunk_TimeSub', f'{name} (Utterance)', participant=participant)
        self.eaf.new_tier(f'{name} (Language)', 'Lang_SymAssoc', f'{name} (Chunk)', participant=participant)
        if target:
            self.eaf.new_tier(f'{name} (Target_EL)', 'Target_Words_Eng_IncIn', f'{name} (Chunk)', participant=participant)
            self.eaf.new_tier(f'{name} (Target_CL)', 'Target_Words_Mandarin_IncIn', f'{name} (Chunk)', participant=participant)
            self.eaf.new_tier(f'{name} (Target_ML)', 'Target_Words_Malay_IncIn', f'{name} (Chunk)', participant=participant)
            self.eaf.new_tier(f'{name} (Target_TL)', 'Baby_Target_Words_IncIn', f'{name} (Chunk)', participant=participant)
        self.eaf.new_tier(f'{name} (Translation)', 'Translation', f'{name} (Utterance)', participant=participant)
        if matrix:
            self.eaf.new_tier(f'{name} (Matrix)', 'Matrix_Lang', f'{name} (Utterance)', participant=participant)
        if sensitive:
            self.eaf.new_tier(f'{name} (Sensitive_Masking)', 'Sensitive_Masking_IncIn', f'{name} (Utterance)', participant=participant)

    def annotate(self, name, text, from_ts, to_ts, chunks, times, trans):
        ''' Create a new annotation '''
        pu = self.eaf[f'{name} (Utterance)']
        pc = self.eaf[f'{name} (Chunk)']
        pl = self.eaf[f'{name} (Language)']
        pt = self.eaf[f'{name} (Translation)']
        u = pu.new_annotation(text, from_ts, to_ts)
        pt.new_annotation(trans, ann_ref_id=u.ID)
        chunk_texts = [c[0] for c in chunks]
        chunk_langs = [c[1] for c in chunks]
        chunk_objs = pc.new_annotation(None, values=chunk_texts, timeslots=times, ann_ref_id=u.ID)
        for c, l in zip(chunk_objs, chunk_langs):
            pl.new_annotation(l, ann_ref_id=c.ID)
        return pu

    def to_csv_rows(self, *args, **kwargs):
        """ Generate CSV content """
        return self.eaf.to_csv_rows(*args, **kwargs)

    def to_xml_bin(self, *args, **kwargs):
        """ Generate EAF content (bytes) in XML format """
        return self.eaf.to_xml_bin(*args, **kwargs)

    def to_xml_str(self, *args, **kwargs):
        """ Generate EAF content string in XML format """
        return self.eaf.to_xml_str(*args, **kwargs)

    def save(self, *args, **kwargs):
        ''' Write BELA transcript to an EAF file '''
        return self.eaf.save(*args, **kwargs)

    def to_bela(self, *args, **kwargs):
        return Bela2.from_elan(self.eaf.clone(), *args, **kwargs)
