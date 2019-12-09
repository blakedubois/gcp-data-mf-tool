import logging
import sys

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])

LOGGER = logging.getLogger('mfutil')
LOGGER.setLevel(logging.INFO)
