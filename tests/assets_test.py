import unittest


from pathlib import Path
from mf.assets import ComponentBase

class TestComponentBase(unittest.TestCase):

    def test_assets(self):
        c = ComponentBase('spark-app', {
            'type': 'someType',
            'metadata': {},
            'assets': [ { 'glob': './**/test_dir/*.txt' } ]
        })

        assets = list(c.assets)
        self.assertEqual(3, len(assets), f'get assets {assets}')

    def test_assets_recursive(self):
        c = ComponentBase('spark-app', {
            'type': 'someType',
            'metadata': {},
            'assets': [ { 'glob': './**/test_dir/**/*.ini' } ]
        })

        assets = list(c.assets)
        self.assertEqual(3, len(assets), f'get assets {assets}')

    def test_assets_props(self):

        dir = Path(__file__).absolute().parent

        c = ComponentBase('spark-app', {
            'type': 'someType',
            'metadata': {},
            'assets': [ { 'glob': './test_dir/*_q*' } ]
        }, dir)

        assets = list(c.assets)
        self.assertEqual(1, len(assets), f'get assets {assets}')

        asset = assets[0]

        self.assertEqual('file_q.txt', asset.filename)
        self.assertEqual('7MvIfktc4v4oMI/Z8qe68w==', asset.md5)
        self.assertEqual(dir / 'test_dir' / 'file_q.txt', asset.path)

    def test_assets_zip(self):

        dir = Path('.').absolute()

        c = ComponentBase('spark-app', {
            'type': 'someType',
            'metadata': {},
            'assets': [ { 'glob': './**/test_dir/**/*.ini', 'zip': True } ]
        }, dir)

        assets = list(c.assets)
        self.assertEqual(1, len(assets), f'get assets {assets}')

        asset = assets[0]

        self.assertEqual('eca250db839ef52ec31316c987c439ff.zip', asset.filename)
        self.assertEqual('7KJQ24Oe9S7DExbJh8Q5/w==', asset.md5)


if __name__ == '__main__':
    unittest.main()