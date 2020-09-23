#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Test script for BELA
Latest version can be found at https://github.com/letuananh/bela

:copyright: (c) 2020 Le Tuan Anh <tuananh.ke@gmail.com>
:license: MIT, see LICENSE for more details.
'''

import os
import unittest
import logging

import bela

TEST_DIR = os.path.dirname(os.path.realpath(__file__))


def getLogger():
    return logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Test cases
# ------------------------------------------------------------------------------

class TestBELA(unittest.TestCase):

    def test_bela(self):
        self.assertEqual(bela.__version__, '0.1a1')
