import os.path
import unittest2
import datetime

from dateminer import DateMiner, guess_date

root = os.path.dirname(__file__)

def get_fixture_data(name):
    return open(os.path.join(root, 'fixtures', name)).read()

TESTS = (
    ('http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2', 'cnn.html', (2010, 5, 20)),
    ('http://businessweek.com/news/2010-10-04/germany-steps-up-bonus-curbs-at-commerzbank-hypo-real-estate.html', 'businessweek.html', (2010, 10, 4)),
    ('http://www.latimes.com/news/nationworld/nation/la-na-texas-death-20110916,0,3367730.story', 'latimes.html', (2011, 9, 15)),
)

class DateMinerTest(unittest2.TestCase):
    def assertDate(self, date1, date2, url, content):
        message = "%s did not match date" % url

        self.assertEquals(date1, date2, message)

    def test_from_url(self):
        dateminer = DateMiner()
        results = list(dateminer.from_url('http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2').sorted())
        self.assertGreater(len(results), 1, results)
        self.assertEquals(results[0], datetime.date(year=2010, month=5, day=20))

    def test_from_html(self):
        dateminer = DateMiner()
        results = list(dateminer.from_html(get_fixture_data('cnn.html')).sorted())
        self.assertGreater(len(results), 1, results)
        self.assertEquals(results[0], datetime.date(year=2010, month=5, day=20))
