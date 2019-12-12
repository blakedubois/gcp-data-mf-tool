# coding: utf-8

import logging
import sys

formatter = logging.Formatter("%(levelname)s %(module)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logging.basicConfig(handlers=[handler])

LOGGER = logging.getLogger('mfutil')
LOGGER.setLevel(logging.ERROR)
