import os.path
import unittest2

from dateminer import DateMiner

root = os.path.dirname(__file__)

def get_fixture_data(name):
    return open(os.path.join(root, 'fixtures', name)).read()

class DateMinerTest(unittest2.TestCase):
    def test_cnn_url(self):
        url = 'http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2'
        content = ''
        tu = DateMiner()
        date = tu.coerce_dates(url, content)
        self.assertEquals(date.month, 5)
        self.assertEquals(date.day, 20)
        self.assertEquals(date.year, 2010)

    def test_cnn_content(self):
        url = 'http://www.cnn.com/gulf.oil.spill/index.html?hpt=T2'
        content = get_fixture_data('cnn.html')
        tu = DateMiner()
        date = tu.coerce_dates(url, content)
        self.assertEquals(date.month, 5)
        self.assertEquals(date.day, 20)
        self.assertEquals(date.year, 2010)
