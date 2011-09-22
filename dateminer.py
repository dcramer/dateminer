#
"""
dateminer
~~~~~~~~~

Python port of John Muellerleile's dateminer Java library:

  https://github.com/jrecursive/date_miner

:copyright: (c) 2011 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""


from lxml import etree
from datetime import date
import itertools
import re
import sys

def guess_date(url, content):
    dateminer = DateMiner()
    results = dateminer.parse(url, content)

    if not results:
        return

    return list(results.sorted())[0]

class Results(object):
    def __init__(self, results=None):
        self.results = results or []
        self.cur_year = date.today().year

    def __iter__(self):
        return iter(self.results)

    def __repr__(self):
        return '<%s: results=%s>' % (self.__class__.__name__, self.results)

    def __len__(self):
        return len(self.results)

    def __getitem__(self, *args, **kwargs):
        return self.results.__getitem__(*args, **kwargs)

    def __getslice__(self, *args, **kwargs):
        return self.results.__getslice__(*args, **kwargs)

    def sorted(self):
        scored = ((k, sum(x.score for x in v)) for k, v in itertools.groupby(self.results, key=lambda x: x.date))

        for d, s in sorted(scored, key=lambda x: x[1], reverse=True):
            yield d

    def add(self, guess, where):
        if not guess.year:
            return
        if guess.year > self.cur_year:
            return
        self.results.append(guess)

    def update(self, results):
        if not results:
            return

        if isinstance(results, Results):
            self.results.extend(results.results)
        else:
            self.results.extend(results)

class Guess(object):
    def __init__(self, year=None, month=None, day=None):
        self.year = year
        self.month = month
        self.day = day

    def __repr__(self):
        return '<%s: date=%s, score=%s>' % (self.__class__.__name__, self.date, self.score)

    def __eq__(self, other):
        if isinstance(other, Guess):
            return self.year == other.year and self.month == other.month and self.day == other.day
        raise ValueError

    @property
    def score(self):
        return sum(map(lambda x: bool(x), [self.year, self.month, self.day]))

    @property
    def date(self):
        return date(year=self.year or date.today().year, month=self.month or 1, day=self.day or 1)

class DateParser(object):
    # we dont include script tags as some sites (cnn) dont seem to hardcode the date
    useless_tags = ['style']

    def __init__(self, miner):
        self.miner = miner
        self.dates = []
        self.parse = True

    def start(self, tag, attr):
        if tag in self.useless_tags:
            self.parse = False

    def end(self, tag):
        if tag in self.useless_tags:
            self.parse = True

    def data(self, data):
        if self.parse:
            self.dates.extend(self.miner.from_text(data.strip()))

    def close(self):
        return self.dates

class DateMiner(object):
    months_short = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    months_long = ['january', 'february', 'march', 'april', 'may',
                   'june', 'july', 'august', 'september', 'october',
                   'november', 'december']

    _re_collapse_chars = re.compile(r'[\/\_\-\?\.\&=,]')
    _re_alpha = re.compile(r'[A-Za-z]+')

    def __init__(self):
        self.results = []
        self.cur_year = date.today().year

    def find_dates_in_text(self, text, where='text'):
        chunks = text.split(' ')

        guess = Guess()
        results = Results()

        cur_chunk = 0
        num_chunks = len(chunks)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            chunk_len = len(chunk)

            if not chunk.isdigit():
                if chunk_len == 3:
                    try:
                        guess.month = self.months_short.index(chunk.lower())
                    except ValueError:
                        pass

                elif chunk_len > 3:
                    try:
                        guess.month = self.months_long.index(chunk.lower())
                    except ValueError:
                        pass

                elif guess.year and guess.month:
                    results.add(guess, where)
                    guess = Guess()

            else:
                tval = None
                if chunk_len in (8, 12):
                    tval = self.brute_force_date(chunk, 8)

                elif chunk_len == 6:
                    s6_mmdd = chunk[:4]
                    if int(chunk[4:6]) < 70:
                        s6_yyyy = "20" + chunk[4:6]
                    else:
                        s6_yyyy = "19" + chunk[4:6]
                    tval = self.brute_force_date(s6_mmdd + s6_yyyy, 8)

                elif chunk_len == 4:
                    v1 = int(chunk)
                    if v1 > 1900 and v1 <= self.cur_year:
                        guess.year = v1
                    else:
                        if not (guess.month or guess.day):
                            v1 = int(chunk[:2])
                            v2 = int(chunk[2:4])

                            # assumes mm, dd first if either would match
                            if (v1 > 0 and v1 <= 12 and v2 > 0 and v2 <= 31):
                                guess.month = v1
                                guess.day = v2
                            elif (v1 > 0 and v1 <= 31 and v2 > 0 and v2 <= 12):
                                guess.month = v2
                                guess.day = v1
                        else:
                            # we thought we found a month, but it turns out to
                            # be something like this: /03/1114/ which usually
                            # [at this state] turns out to be: 11/14/2003
                            if guess.month:
                                s4_2then4 = '%s20%s%s' % (chunk, (guess.month < 10 and "0" or ""), guess.month)
                                tval = self.brute_force_date(s4_2then4, 8)
                                guess = Guess()
                elif chunk_len in (1, 2):
                    if chunk_len == 1:
                        chunk = "0" + chunk

                    pos_v = int(chunk)

                    # if we have month and day already and it's length 2,
                    # it's probably a shortened year... let's do the 2069 test
                    if not guess.year and (guess.month and guess.day and chunk_len == 2):
                        if pos_v < 70:
                            if pos_v + 2000 <= self.cur_year:
                                guess.year = 2000 + pos_v
                        else:
                            guess.year = 1900 + pos_v

                    # try parsing a month or day
                    # since we don't have both month and day found yet
                    # (reality may differ)
                    else:
                        if pos_v > 0 and pos_v <= 12:
                            if not guess.month:
                                guess.month = pos_v
                            else:
                                guess.day = pos_v
                        elif pos_v > 0 and pos_v <= 31 and not guess.day:
                            guess.day = pos_v
                        else:
                            # since at this point we've found either a month or a day, OR
                            # the value presented at this state is not a candidate for what
                            # CAN be found, IF we've got a year then let's add that as a date
                            # (best guess), and augment with month if we've got that
                            if guess.year:
                                uc_s2_uk2 = str(guess.year)
                                if guess.month:
                                    uc_s2_uk2 += (guess.month < 10 and "0" or "") + str(guess.month)
                                else:
                                    uc_s2_uk2 += "01" # default month
                                uc_s2_uk2 += "01" # default day
                                tval = self.brute_force_date(uc_s2_uk2, 8)
                else:
                    if chunk_len >= 8:
                        tval = self.brute_force_date(chunk, 8)

                if tval:
                    results.add(tval, where)
                    guess = Guess()
                # elif guess.year:
                #     results.add(guess, where)
                #     guess = Guess()

            # last chance
            cur_chunk += 1
            if guess.year and guess.month and cur_chunk == num_chunks - 1:
                results.add(guess, where)
                guess = Guess()

        if guess.year:
            results.add(guess, where)
            guess = Guess()

        return results

    def brute_force_date(self, string, valid):
        guess = None

        s1_1_4 = int(string[:4])
        s1_2_2 = int(string[4:6])
        s1_3_2 = int(string[6:8])

        s2_1_2 = int(string[:2])
        s2_2_2 = int(string[2:4])
        s2_3_4 = int(string[4:8])

        if (s1_1_4 > 1900 and
           s1_1_4 < (self.cur_year + 1) and # yy
           s1_2_2 > 0 and
           s1_2_2 <= 12 and # mm
           s1_3_2 > 0 and
           s1_3_2 <= 31): #dd

            guess = Guess(year=s1_1_4, month=s1_2_2, day=s1_3_2)

        elif (s2_3_4 > 1900 and
             s2_3_4 < (self.cur_year + 1)):
             # s2, s2_3_4 -> yy

            # dd mm yyyy?
            if (s2_1_2 > 0 and
               s2_1_2 <= 31 and
               s2_2_2 > 0 and
               s2_2_2 <= 12):

                guess = Guess(year=s2_3_4, month=s2_2_2, day=s2_1_2)

            # mm dd yyyy?
            elif (s2_1_2 > 0 and
                 s2_1_2 <= 12 and
                 s2_2_2 > 0 and
                 s2_2_2 <= 31):

                guess = Guess(year=s2_3_4, month=s2_1_2, day=s2_2_2)

        return guess

    def collapse_chars(self, text):
        return self._re_collapse_chars.sub(' ', text)

    def from_url(self, url):
        url = url.split('//', 1)[1]
        try:
            url = url.split('/', 1)[1]
        except IndexError:
            url = ''

        url = self.collapse_chars(url)

        return self.from_text(url, 'url')

    def from_text(self, text, where='text'):
        text = self.collapse_chars(text)

        out = ''
        chunks = text.split(' ')
        for chunk in chunks:
            chunk = chunk.strip().lower()

            if not chunk:
                continue

            if not (chunk in self.months_short or chunk in self.months_long):
                chunk = self._re_alpha.sub(' ', chunk)

            out += chunk + " "

        out = out.strip()

        results = self.find_dates_in_text(text, where)
        if out != text:
            results.update(self.find_dates_in_text(out, where))

        return results

    def from_html(self, content):
        dtparser = DateParser(miner=self)
        parser = etree.HTMLParser(target=dtparser)
        parser.feed(content)
        return Results(parser.close())

    def parse(self, url, content):
        results = self.from_url(url)
        html_results = self.from_html(content)
        # TODO: this should reweight any matches found in the content so that they're
        # prioritized, and should happen in ``Results``
        if not (any(r.score >= 3 for r in results) or any(r in results for r in html_results)):
            results.update(html_results)

        return results

if __name__ == '__main__':
    import urllib2

    if len(sys.argv) == 1:
        url = "http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2"
    else:
        url = ' '.join(sys.argv[1:])
    content = urllib2.urlopen(url).read()

    dateminer = DateMiner()
    print dateminer.parse(url, content)