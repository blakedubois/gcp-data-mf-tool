import unittest
import requests
from datetime import datetime, time
from typing import Tuple, Optional

from mf.manifest import Manifest, StorageBase
from mf.config import BuildInfo, Project


class StorageMock(StorageBase):

    def fetch_manifest(self) -> Tuple[str, int, dict]:
        return 'some/key/here', 100, {
            '@ns': {}
        }

    def cas_blob(self, data: bytes, generation: int, bucket_name: str, blob_name: str) -> Tuple[
        bool, Optional[requests.Response]]:
        return super().cas_blob(data, generation, bucket_name, blob_name)

    def upload(self, bucket, key, file):
        return super().upload(bucket, key, file)


class TestComponentBase(unittest.TestCase):

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

        expected = {
            '@ns': {'dev': {'@last_success': {
                                                 '@build_id': 'aaaa-bbb-ccc',
                                                 '@built_at': '2018-11-01T05:01:01.000001+00:00',
                                                 '@rev': '431refrqewr',
                                                 '@include': {
                                                     'spark': {'@binaries': [{'@md5': '1B2M2Y8AsgTpgAmY7PhCfg==',
                                                                              '@ref': 'gs://BUCKET/ARepo/dev/431refrqewr/spark/test_file.cfg'}],
                                                               '@metadata': {},
                                                               '@type': 'some'}
                                                 }
                                                 }
                               }
                    }
        }

        self.assertEqual(expected, content)

if __name__ == '__main__':
    unittest.main()