# coding: utf-8

import copy
import json
from pathlib import Path
from typing import Tuple, Optional, Dict

import google
import datetime
import requests
import warnings
import requests.auth

from jsonpath_ng import jsonpath, parse
from slugify import slugify
from google.cloud import storage
from urllib.parse import urlparse

from mf.config import Project, BuildInfo
from mf.assets import AssetBase
from mf.log import LOGGER

MANIFEST_NAME = 'manifest.json'


class StorageBase:

    def fetch_manifest(self) -> Tuple[str, int, dict]:
        raise NotImplemented('fetch_manifest')

    def cas_blob(self, data: bytes, generation: int, bucket_name: str, blob_name: str) -> Tuple[
        bool, Optional[requests.Response]]:
        raise NotImplemented('cas_blob')

    def upload(self, bucket, key, file: Path):
        raise NotImplemented('upload')

    def download(self, bucket, key, file):
        raise NotImplemented('upload')


class StorageGCS(StorageBase):

    def __init__(self, bucket, semantic_name):

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            credentials, _ = google.auth.default()
            self._storage_client = storage.Client(credentials=credentials)
            self._credentials = credentials

        self._semantic_name = semantic_name
        self._gs_bucket: storage.Bucket = self._storage_client.lookup_bucket(bucket)

        if not self._gs_bucket.versioning_enabled:
            msg = f"Object Versioning for bucket [ {self._gs_bucket.name} ] is not enabled. " \
                "This can lead to a potential loss of updates while being published by multiple clients. " \
                "Please enable it for further usage. \n" \
                f"Simplest way is to fix it   gsutil versioning set on gs://{self._gs_bucket.name} ` \n" \
                "More information - https://cloud.google.com/storage/docs/gsutil/addlhelp/ObjectVersioningandConcurrencyControl"
            raise RuntimeError(msg)

    def fetch_manifest(self) -> Tuple[str, str, dict]:
        """
        Fetch manifest from GS bucket. Remember blob's generation for concurrency control.
        :return:
        """
        bucket = self._gs_bucket

        key = f'{self._semantic_name}/{MANIFEST_NAME}'
        manifest_blob: storage.bucket.Blob = bucket.get_blob(key)

        if not manifest_blob:
            LOGGER.warning(f'{MANIFEST_NAME} not exists by  gs://{bucket.name}/{key}, create empty')
            empty_manifest: str = json.dumps({"@spec": 1, "@ns": {}})

            ok, err = self.cas_blob(empty_manifest.encode('utf-8'),
                                    generation=0, bucket_name=bucket.name, blob_name=key)

            if ok or err is None:
                # manifest has just created
                manifest_blob = bucket.get_blob(key)
            else:
                LOGGER.error("Could not create manifest %s", err.content)
                raise Exception("creating %s failed" % key)

        str_ = manifest_blob.download_as_string()
        json_ = json.loads(str_)

        LOGGER.debug('Fetching manifest -- gs://%s/%s#%d', manifest_blob.bucket.name, manifest_blob.name,
                     manifest_blob.generation)
        return manifest_blob.name, manifest_blob.generation, json_

    def cas_blob(self, data: bytes, generation: int, bucket_name: str, blob_name: str) -> Tuple[
        bool, Optional[requests.Response]]:
        """
        Perform analog of compare-and-set operation on GoogleStorage object.

        Unfortunately google.cloud api don't provide 'if-generation-match' similar mechanics so
        JSON API was used for this purpose.

        :param bucket_name:
        :param blob_name:
        :param data: data to post
        :param generation: expected blob's generation
        :return: (true, None) - if update success;
                 (false, None) - on conflict; (false, response) - on any other http error
        """

        class AuthBearer(requests.auth.AuthBase):
            def __init__(self, t):
                self._token = t

            def __call__(self, r):
                r.headers['Authorization'] = f'Bearer {self._token}'
                return r

        # TODO add retry ?
        oauth_token = self._credentials.token
        link = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o"

        headers = {
            'x-goog-if-generation-match': str(generation)
        }

        resp = requests.post(link, data=data, params={'uploadType': 'media', 'name': blob_name},
                             headers=headers, auth=AuthBearer(oauth_token))

        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 412:
            return False, None
        else:
            return False, resp

    def upload(self, bucket, key, file):
        """
        Upload file into bucket and key
        :param bucket: bucket
        :param key: key
        :param file: file
        :return:
        """
        blob: storage.client.Blob = self._storage_client.bucket(bucket).blob(key)
        blob.upload_from_filename(filename=str(file))

    def download(self, bucket, key, file):
        blob: storage.Blob = self._storage_client.bucket(bucket).blob(key)
        blob.download_to_filename(str(file))


class Manifest(object):

    def __init__(self, bucket, repo_name, **kwargs):

        self._bucket = bucket
        self._repo_name = repo_name

        if 'storage' in kwargs:
            self._storage: StorageBase = kwargs['storage']
        else:
            self._storage: StorageBase = StorageGCS(bucket, repo_name)

        self.__fetch_manifest()

    def __fetch_manifest(self):
        blob_name, version, content = self._storage.fetch_manifest()

        self._original_content = content
        self._version = version
        self._blob_key = blob_name

    @property
    def content(self):
        return copy.deepcopy(self._original_content)

    def download(self, binary: dict, dest):
        path = binary['url'].replace('gs://', '')

        path_parts = path.split('/')
        bucket = path_parts[0]
        key = "/".join(path_parts[1:])
        filename = path_parts[len(path_parts) - 1]

        folders = Path(dest) / binary['branch'] / binary['app']
        if not folders.exists():
            folders.mkdir(parents=True)

        file = folders / filename

        self._storage.download(bucket, key, file)

    def search(self, branch_name=None, app_name=None):
        from jsonpath_ng.jsonpath import Fields, Slice

        if branch_name is None:
            branch_name = '*'
        else:
            branch_name = slugify(branch_name)

        if app_name is None: app_name = '*'

        acc = []
        for branch in parse(f'$.@ns.{branch_name}').find(self._original_content):
            for build in Fields('@last_success').find(branch.value):
                for app in Fields(f'@include').child(Fields(app_name)).find(build.value):
                    acc.extend([
                        {
                            'branch': str(branch.path),
                            'app': str(app.path),
                            'built_at': str(build.value['@built_at']),
                            'commit': str(build.value['@rev']),
                            'url': str(bin['@ref']),
                        } for bin in app.value.get('@binaries', []) if '@ref' in bin
                    ])

        sorted(acc, key=lambda d: (d['branch'], d['app']))

        return acc

    def update(self, build: BuildInfo, project_obj: Project, upload: bool = True):
        """
        Compare and update blob by generation.
        Trying until success.

        :param build: build info
        :param upload: to do uploading of a content, (for debug)
        :param project_obj:
        """

        refs_upload_done = False

        while True:
            current_manifest, assets = _merge_new_manifest(self._original_content, build, project_obj)

            if not upload:
                return current_manifest

            # Upload assets first and update manifest only after it.
            if not refs_upload_done:
                refs_upload_done = True

                for key, file in assets.items():
                    LOGGER.debug("Uploading %s [%s]", file, key)
                    self._storage.upload(project_obj.bucket, key, file.absolute())

                LOGGER.info("Uploading done for %d objects", len(assets))

            ok, err_resp = self._storage.cas_blob(data=json.dumps(current_manifest).encode('utf-8'),
                                                  generation=self._version,
                                                  bucket_name=self._bucket,
                                                  blob_name=self._blob_key)
            if ok:
                return current_manifest
            elif err_resp is None:
                # TODO any logic to resolve conflict in the content ?
                LOGGER.warning("manifest have already been modified, retry...")
                self.__fetch_manifest()
            else:
                LOGGER.error("update failed [%s] %s", err_resp.status_code, err_resp.text)
                raise Exception('GoogleStorage update failed')


def _merge_new_manifest(original_manifest: dict, build: BuildInfo, mf_file: Project) \
        -> Tuple[dict, Dict[str, Path]]:
    """
    Merge generated manifest about branch into fetched from remote.

    :param original_manifest: original manifest content
    :param build: build info
    :param mf_file: config file
    :return: resulting whole manifest and assets
    """

    current_manifest = copy.deepcopy(original_manifest)
    ns_key = '@ns'

    if ns_key not in current_manifest:
        current_manifest[ns_key] = {}

    ns = current_manifest[ns_key]

    assets: Dict[str, Path] = dict()

    def ref(component_name, asset: AssetBase):
        key = f'{mf_file.repository}/{build.git_branch}/{build.git_sha}/{component_name}/{asset.filename}'
        url = f'gs://{mf_file.bucket}/{key}'
        path = asset.path

        LOGGER.debug("[%s] discovering asset %s", component_name, path)
        if key not in assets:
            assets[key] = asset.path

        return url

    component_dict = dict(
        [(component.name, {
            "@type": component.type,
            "@metadata": {},
            "@binaries": [{
                "@md5": asset.md5,
                "@ref": ref(component.name, asset)
            } for asset in component.assets]
        }) for component in mf_file.components]
    )

    ns[build.git_branch] = {
        "@last_success": {
            "@built_at": build.date.replace(tzinfo=datetime.timezone.utc).isoformat(),
            "@rev": build.git_sha,
            "@build_id": build.build_id,
            "@include": component_dict
        }
    }

    return current_manifest, assets
