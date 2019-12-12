# coding: utf-8

import logging
import sys

logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)])

LOGGER = logging.getLogger('mfutil')
LOGGER.setLevel(logging.ERROR)
