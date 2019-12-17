# coding: utf-8

import datetime
import json

from mf.log import LOGGER
from mf.assets import ComponentBase
from pathlib import Path
from typing import Union, Optional

from slugify import slugify

from jsonschema import validate

#
# Default configuration file name.
#
DEFAULT_CONFIG_FILE_NAME = ".mf.json"

#
# This is a jsonschema for config file
# see: https://json-schema.org/understanding-json-schema/index.html
#
_SCHEMA = {
    "type": "object",
    "required": ["bucket", "repository", "components"],
    "properties": {
        "bucket": {"type": "string"},
        "repository": {"type": "string"},
        "components": {
            "type": "object",
            "propertyNames": {
                "pattern": "^[-a-zA-Z0-9_]*$"
            },
            "additionalProperties": {
                "type": "object",
                "required": ["type", "assets"],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                    "assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "glob": {"type": "string"},
                                "zip": {"type": "boolean"},
                            }
                        }
                    },
                }

            }
        },
    }
}


class Project:
    """
    Project description.

    Describes:
     - assets
     - target bucket as a storage
     - project semantic name

    """

    def __init__(self, cfg: dict, root_dir: Path = Path().absolute()):
        self._cfg = cfg
        self._root_dir = root_dir

    @property
    def components(self):
        return [ComponentBase(name, json, self._root_dir) for name, json in self._cfg['components'].items()]

    @property
    def bucket(self):
        return self._cfg['bucket']

    @property
    def repository(self):
        return self._cfg['repository']

    def __repr__(self):
        return 'Conf{\n%s\n}' % (',\n'.join(['\t{}={}'.format(a, b) for a, b in self._cfg.items()]))


def read_config(root: Path, mf_file: Optional[Union[Path, bytes, str, dict]] = None) -> Optional[Project]:

    def _load_json(data):
        json_ = json.load(data) if hasattr(data, 'read') else json.loads(data)
        validate(instance=json_, schema=_SCHEMA)
        assert len(json_) > 0, 'json is an empty object'
        return json_

    if mf_file is not None:

        if isinstance(mf_file, bytes) or isinstance(mf_file, str):
            return Project(_load_json(mf_file), root)
        elif isinstance(mf_file, dict):
            return Project(mf_file, root)

    conf_file_path = Path(mf_file) if mf_file else root / DEFAULT_CONFIG_FILE_NAME
    if not conf_file_path.exists():
        LOGGER.warning("config file not exists [%s]", conf_file_path)
        return None

    with open(conf_file_path, 'r') as f:
        cfg = _load_json(f)
        file = Project(cfg, root)
        return file


class BuildInfo(object):

    def __init__(self, git_sha: str, git_branch: str, build_id: str,
                 date: datetime.datetime = datetime.datetime.utcnow()):
        self.git_sha = git_sha
        self._git_branch = git_branch
        self.date = date
        self.build_id = build_id

    @property
    def git_branch(self):
        return slugify(self._git_branch)
