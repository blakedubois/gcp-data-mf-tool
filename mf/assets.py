import hashlib
import base64
import tempfile
import os

from typing import Tuple

from zipfile import ZipFile
from typing import Iterable, Generator
from pathlib import Path

_data_holder_attr = '_lazy_properties'


# noinspection PyPep8Naming
class lazy_property(object):
    """lazy property decorator, just like built-in `property`"""

    def __init__(self, fget):
        self.fget = fget
        self.property_name = fget.__name__

    def get_lazy_data(self, instance):
        if not hasattr(instance, _data_holder_attr):
            setattr(instance, _data_holder_attr, {})
        return getattr(instance, _data_holder_attr)

    def __get__(self, instance, owner):
        if instance is None:
            return None

        lazy_data = self.get_lazy_data(instance)

        if self.property_name in lazy_data:
            return lazy_data[self.property_name]

        value = self.fget(instance)
        lazy_data[self.property_name] = value
        return value


class AssetBase:

    def __init__(self, **kwargs):
        pass

    @property
    def md5(self) -> str:
        raise NotImplemented('md5')

    @property
    def path(self) -> Path:
        raise NotImplemented('path')

    @property
    def filename(self) -> str:
        raise NotImplemented('filename')

    @lazy_property
    def _md5_(self) -> Tuple[str, str]:
        return _calc_md5_(self.path)


class RawAsset(AssetBase):

    def __init__(self, file: Path, **kwargs):
        super().__init__(**kwargs)
        self._file: Path = file

    @property
    def md5(self):
        return self._md5_[0]

    @property
    def path(self) -> Path:
        return self._file

    @property
    def filename(self) -> str:
        return self.path.name


class ZipAsset(AssetBase):

    def __init__(self, files: Iterable[Path], **kwargs):
        super().__init__(**kwargs)
        self._files = list(files)
        sorted(self._files, key=lambda p: p.name)

    @lazy_property
    def __tarball__(self) -> Path:
        with tempfile.NamedTemporaryFile(delete=False, prefix='tarball') as nf:
            with ZipFile(nf, 'w') as zf:
                # keep the structure of file the same as glob discovered
                common_root_dir = Path(os.path.commonpath([str(x.absolute()) for x in self._files]))
                for f in self._files:
                    # noinspection PyTypeChecker
                    relative = os.path.relpath(f, start=common_root_dir)
                    zf.write(f, relative)
            return Path(nf.name)

    @lazy_property
    def md5(self) -> str:
        return self._md5_[0]

    @property
    def path(self) -> Path:
        return self.__tarball__

    @property
    def filename(self) -> str:
        return f'{self._md5_[1]}.zip'


class ComponentBase:

    def __init__(self, name, _json, root_dir=Path().absolute()):
        self.name = name
        self.type: str = str(_json['type'])
        self._assets: Iterable[dict] = _json['assets']

        self._dir: Path = root_dir

    @property
    def assets(self):
        for asset in self._assets:
            glob_ptn = asset['glob']
            is_zip = asset.get('zip', False)

            if is_zip:
                yield ZipAsset(files=[Path(p) for p in self._dir.glob(glob_ptn)])
            else:
                for file in self._dir.glob(glob_ptn):
                    yield RawAsset(file=Path(file))


def _calc_md5_(path, chunk_size=8192) -> Tuple[str, str]:
    """
     Base64 encoded MD5 hash of a file.
     Same as GCS metadata label "Hash (md5)"
    """
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(chunk_size)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(chunk_size)

        return base64.b64encode(file_hash.digest()).decode('utf-8'), file_hash.hexdigest()
