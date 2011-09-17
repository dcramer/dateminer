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
    # TODO
    # ('http://www.latimes.com/news/nationworld/nation/la-na-texas-death-20110916,0,3367730.story', 'latimes.html', (2011, 9, 15)),
)

class DateMinerTest(unittest2.TestCase):
    def assertDate(self, date1, date2, url, content):
        message = "%s did not match date" % url
        
        self.assertEquals(date1, date2, message)

    def test_guess_date(self):
        for url, fixture_name, date in TESTS:
            base_date = datetime.date(year=date[0], month=date[1], day=date[2])
            
            content = get_fixture_data(fixture_name)
            
            date = guess_date(url, content)
            self.assertDate(date, base_date, url, content)
            
            date = guess_date('http://example.com/', content)
            self.assertDate(date, base_date, url, content)
            
            date = guess_date(url, '')
            self.assertDate(date, base_date, url, content)

    def test_coerce_dates_from_url(self):
        dateminer = DateMiner()
        results = dateminer.coerce_dates_from_url('http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2')
        self.assertEquals(len(results), 1, results)
        self.assertEquals(results[0], datetime.date(year=2010, month=5, day=20))
