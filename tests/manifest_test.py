# coding: utf-8

import unittest
import requests
from datetime import datetime, time
from typing import Tuple, Optional

from mf.manifest import Manifest, StorageBase
from mf.config import BuildInfo, Project


class StorageMock(StorageBase):

    # noinspection PyDefaultArgument
    def __init__(self, content={'@ns': {}}):
        self.content = content

    def fetch_manifest(self) -> Tuple[str, int, dict]:
        return 'some/key/here', 100, self.content

    def cas_blob(self, data: bytes, generation: int, bucket_name: str, blob_name: str) -> Tuple[
        bool, Optional[requests.Response]]:
        return super().cas_blob(data, generation, bucket_name, blob_name)

    def upload(self, bucket, key, file):
        return super().upload(bucket, key, file)


class TestComponentBase(unittest.TestCase):
    SEARCH_DATA = \
        {
            '@ns': {
                'dev': {
                    '@last_success': {
                        '@build_id': 'aaaa-bbb-ccc',
                        '@built_at': '2018-11-01T05:01:01.000001+00:00',
                        '@rev': '111111',
                        '@include': {
                            'spark': {
                                '@binaries': [
                                    {
                                        '@md5': 'AAAA==',
                                        '@ref': 'gs://test_file.cfg'
                                    }
                                ],
                                '@metadata': {},
                                '@type': 'some'
                            }
                        }
                    }
                },
                'master': {
                    '@last_success': {
                        '@build_id': 'kkk-bbb-ddd',
                        '@built_at': '2019-12-01T05:01:01.000001+00:00',
                        '@rev': '222222',
                        '@include': {
                            'spark': {
                                '@binaries': [
                                    {
                                        '@md5': 'BBBB==',
                                        '@ref': 'gs://app.jar'
                                    },
                                    {
                                        '@md5': 'CCCC==',
                                        '@ref': 'gs://app.cfg'
                                    }
                                ],
                                '@metadata': {},
                                '@type': 'pyspark'
                            },
                            'pyspark': {
                                '@binaries': [
                                    {
                                        '@md5': 'XXXXX==',
                                        '@ref': 'gs://main.py'
                                    }
                                ],
                                '@metadata': {},
                                '@type': 'pyspark'
                            }
                        }
                    }
                }
            }
        }


    def test_generate_manifest(self):
        branch_name = 'dev'
        m = Manifest(bucket='BUCKET', repo_name='ARepo', storage=StorageMock())
        b = BuildInfo(git_sha='431refrqewr', git_branch=branch_name,
                      build_id='aaaa-bbb-ccc', date=datetime(2018, 11, 1, 5, 1, 1, 1))

        p = Project({
            'bucket': 'BUCKET',
            'repository': 'ARepo',
            'components': {
                'spark': {
                    'type': 'some',
                    'assets': [
                        {
                            'glob': './**/test_dir/test_file.cfg'
                        }
                    ]
                }
            }
        })

        content = m.update(b, p, False)

        expected = \
            {
                '@ns': {
                    'dev': {
                        '@last_success': {
                            '@build_id': 'aaaa-bbb-ccc',
                            '@built_at': '2018-11-01T05:01:01.000001+00:00',
                            '@rev': '431refrqewr',
                            '@include': {
                                'spark': {
                                    '@binaries': [
                                        {
                                            '@md5': '1B2M2Y8AsgTpgAmY7PhCfg==',
                                            '@ref': 'gs://BUCKET/ARepo/dev/431refrqewr/spark/test_file.cfg'
                                        }
                                    ],
                                    '@metadata': {},
                                    '@type': 'some'
                                }
                            }
                        }
                    }
                }
            }

        self.assertEqual(expected, content)

    def test_search_all(self):

        m = Manifest(bucket='bucket', repo_name='repo', storage=StorageMock(self.SEARCH_DATA))
        found = m.search()
        expected = [
            {'app': 'spark', 'branch': 'dev', 'commit': '111111', 'built_at': '2018-11-01T05:01:01.000001+00:00', 'url': 'gs://test_file.cfg'},
            {'app': 'spark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00', 'url': 'gs://app.jar'},
            {'app': 'spark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00', 'url': 'gs://app.cfg'},
            {'app': 'pyspark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00', 'url': 'gs://main.py'},
        ]
        self.assertEqual(expected, found)

    def test_search_branch(self):

        m = Manifest(bucket='bucket', repo_name='repo', storage=StorageMock(self.SEARCH_DATA))
        found = m.search(branch_name='dev')
        expected = [
            {'app': 'spark', 'branch': 'dev', 'commit': '111111',  'built_at': '2018-11-01T05:01:01.000001+00:00', 'url': 'gs://test_file.cfg'}
        ]
        self.assertEqual(expected, found)

    def test_search_app(self):

        m = Manifest(bucket='bucket', repo_name='repo', storage=StorageMock(self.SEARCH_DATA))
        found = m.search(app_name='spark')
        expected = [
            {'app': 'spark', 'branch': 'dev', 'commit': '111111', 'built_at': '2018-11-01T05:01:01.000001+00:00', 'url': 'gs://test_file.cfg'},
            {'app': 'spark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00', 'url': 'gs://app.jar'},
            {'app': 'spark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00', 'url': 'gs://app.cfg'},
        ]
        self.assertEqual(expected, found)

    def test_search_app_and_branch(self):

        m = Manifest(bucket='bucket', repo_name='repo', storage=StorageMock(self.SEARCH_DATA))
        found = m.search(app_name='pyspark', branch_name='master')
        expected = [
            {'app': 'pyspark', 'branch': 'master', 'commit': '222222', 'built_at': '2019-12-01T05:01:01.000001+00:00',  'url': 'gs://main.py'},
        ]
        self.assertEqual(expected, found)

    def test_search_not_found(self):

        m = Manifest(bucket='bucket', repo_name='repo', storage=StorageMock(self.SEARCH_DATA))
        found = m.search(app_name='no_wired_no_world')
        expected = []
        self.assertEqual(expected, found)



if __name__ == '__main__':
    unittest.main()
