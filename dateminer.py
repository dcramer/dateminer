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
    results = dateminer.coerce_dates(url, content)

    if not results:
        return

    grouped_by_date = dict((k, len(list(v))) for k, v in itertools.groupby(results, key=lambda x: x))

    # TODO: if multiple match same count then we should take the newest date
    best = (0, None)
    for dt, matches in grouped_by_date.items():
        if best[0] < matches or (best[0] == matches and dt > best[1]):
            best = (matches, dt)
    
    return best[1]

class DateParser(object):
    def __init__(self, miner):
        self.miner = miner
        self.dates = []

    def data(self, data):
        self.dates.extend(self.miner.coerce_dates_from_text(data.strip()))

class DateMiner(object):
    months_short = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    months_long = ['january', 'february', 'march', 'april', 'may',
                   'june', 'july', 'august', 'september', 'october',
                   'november', 'december']

    def find_dates_in_text(self, text):
        chunks = text.split(' ')

        results = []

        dt = date.today()

        cur_year = dt.year

        found_year = False
        found_month = False
        found_day = False
        pos_year = 0
        pos_month = 0
        pos_day = 0

        cur_chunk = 0
        num_chunks = len(chunks)
        for chunk in chunks:
            chunk_len = len(chunk)
            chunk = chunk.strip()
            if not chunk:
                continue
            is_num = chunk.isdigit()

            if not is_num:
                pos_month = None
                if chunk_len == 3:
                    try:
                        pos_month = self.months_short.index(chunk.lower())
                    except ValueError:
                        pass
                elif chunk_len > 3:
                    try:
                        pos_month = self.months_long.index(chunk.lower())
                    except ValueError:
                        pass
                else:
                    if found_year:
                        if not found_day:
                            pos_day = 1
                        if not found_month:
                            pos_month = 1

                        results.append(date(year=pos_year, month=pos_month, day=pos_day))

                    found_year = False
                    found_month = False
                    found_day = False
                    pos_year = 0
                    pos_month = 0
                    pos_day = 0

            else:
                tval = 0
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
                    if v1 > 1900 and v1 <= cur_year:
                        pos_year = v1
                        found_year = True
                    else:
                        if not (found_month or found_day):
                            v1 = int(chunk[:2])
                            v2 = int(chunk[2:4])

                            # assumes mm, dd first if either would match
                            if (v1 > 0 and v1 <= 12 and v2 > 0 and v2 <= 31):
                                pos_month = v1
                                pos_day = v2
                                found_month = True
                                found_day = True
                            elif (v1 > 0 and v1 <= 31 and v2 > 0 and v2 <= 12):
                                pos_month = v2
                                pos_day = v1
                                found_month = True
                                found_day = True
                        else:
                            # we thought we found a month, but it turns out to
                            # be something like this: /03/1114/ which usually
                            # [at this state] turns out to be: 11/14/2003
                            if found_month:
                                s4_2then4 = chunk + "20" + (pos_month < 10 and "0" or "") + pos_month
                                tval = self.brute_force_date(s4_2then4, 8)
                                found_month = False
                                found_day = False
                                found_year = False
                                pos_year = 0
                                pos_month = 0
                                pos_day = 0
                elif chunk_len in (1, 2):
                    if chunk_len == 1:
                        chunk = "0" + chunk

                    pos_v = int(chunk)

                    # if we have month and day already and it's length 2,
                    # it's probably a shortened year... let's do the 2069 test
                    if not found_year and (found_month and found_day and chunk_len == 2):
                        if pos_v < 70:
                            if pos_v + 2000 <= cur_year:
                                pos_year = 2000 + pos_v
                        else:
                            pos_year = 1900 + pos_v

                        if pos_year <= cur_year:
                            found_year = True
                        else:
                            pos_year = 0
                            found_year = False

                    # try parsing a month or day
                    # since we don't have both month and day found yet
                    # (reality may differ)
                    else:
                        if pos_v > 0 and pos_v <= 12:
                            if not found_month:
                                pos_month = pos_v
                                found_month = True
                            else:
                                pos_day = pos_v
                                found_day = True
                        elif pos_v > 0 and pos_v <= 31 and not found_day:
                            pos_day = pos_v
                            found_day = True
                        else:
                            # since at this point we've found either a month or a day, OR
                            # the value presented at this state is not a candidate for what
                            # CAN be found, IF we've got a year then let's add that as a date
                            # (best guess), and augment with month if we've got that
                            if found_year:
                                uc_s2_uk2 = str(pos_year)
                                if found_month:
                                    uc_s2_uk2 += (pos_month < 10 and "0" or "") + str(pos_month)
                                else:
                                    uc_s2_uk2 += "01" # default month
                                uc_s2_uk2 += "01" # default day
                                tval = self.brute_force_date(uc_s2_uk2, 8)
                else:
                    if chunk_len >= 8:
                        tval = self.brute_force_date(chunk, 8)

                if tval:
                    results.append(tval)

                    found_year = False
                    found_month = False
                    found_day = False
                    pos_year = 0
                    pos_month = 0
                    pos_day = 0
                    tval = 0
                elif found_year and found_month and found_day:
                    results.append(date(year=pos_year, month=pos_month, day=pos_day))

                    found_year = False
                    found_month = False
                    found_day = False
                    pos_year = 0
                    pos_month = 0
                    pos_day = 0
                    tval = 0

            # last chance
            cur_chunk += 1
            if found_year and found_month and cur_chunk == num_chunks - 1:
                if not found_day:
                    pos_day = 1
                results.append(date(year=pos_year, month=pos_month, day=pos_day))

        if found_year:
            if not found_day:
                pos_day = 1
            if not found_month:
                pos_month = 1
            results.append(date(year=pos_year, month=pos_month, day=pos_day))

        # sanity check
        results = [r for r in results if r.year <= cur_year]

        return results

    def brute_force_date(self, string, valid):
        rdt = None
        cur_year = date.today().year

        s1_1_4 = int(string[:4])
        s1_2_2 = int(string[4:6])
        s1_3_2 = int(string[6:8])

        s2_1_2 = int(string[:2])
        s2_2_2 = int(string[2:4])
        s2_3_4 = int(string[4:8])

        if (s1_1_4 > 1900 and
           s1_1_4 < (cur_year + 1) and # yy
           s1_2_2 > 0 and
           s1_2_2 <= 12 and # mm
           s1_3_2 > 0 and
           s1_3_2 <= 31): #dd

            rdt = date(year=s1_1_4, month=s1_2_2, day=s1_3_2)

        elif (s2_3_4 > 1900 and
             s2_3_4 < (cur_year + 1)):
             # s2, s2_3_4 -> yy

            # dd mm yyyy?
            if (s2_1_2 > 0 and
               s2_1_2 <= 31 and
               s2_2_2 > 0 and
               s2_2_2 <= 12):

                rdt = date(year=s2_3_4, month=s2_2_2, day=s2_1_2)

            # mm dd yyyy?
            elif (s2_1_2 > 0 and
                 s2_1_2 <= 12 and
                 s2_2_2 > 0 and
                 s2_2_2 <= 31):

                rdt = date(year=s2_3_4, month=s2_1_2, day=s2_2_2)

        return rdt
    
    def collapse_chars(self, text):
        return re.sub('[\/\_\-\?\.\&=,]', ' ', text)

    def coerce_dates_from_url(self, url):
        url = url.split('//', 1)[1]
        try:
            url = url.split('/', 1)[1]
        except IndexError:
            url = ''
            
        url = self.collapse_chars(url)
        
        return self.coerce_dates_from_text(url)
        
    def coerce_dates_from_text(self, text):
        text = self.collapse_chars(text)

        out = ''
        chunks = text.split(' ')
        for chunk in chunks:
            chunk = chunk.strip().lower()
            is_month_token = False
            for month in self.months_short:
                if chunk == month:
                    is_month_token = True

            if not is_month_token:
                chunk = re.sub(r'[A-Za-z]+', ' ', chunk)
                if not chunk.strip():
                    continue

            out += chunk + " "

        out = out.strip()

        results = set(self.find_dates_in_text(text))
        if out != text:
            results.update(set(self.find_dates_in_text(out)))

        return list(results)

    def coerce_dates_from_html(self, content):
        dtparser = DateParser(miner=self)
        parser = etree.HTMLParser(target=dtparser)
        parser.feed(content)

        return dtparser.dates

    def coerce_dates(self, url, content):
        dates_url = set(self.coerce_dates_from_url(url))
        dates_content = set(self.coerce_dates_from_html(content))

        results = dates_url.intersection(dates_content)

        if len(results) != 1:
            if dates_url and not dates_content:
                results.update(dates_url)
            elif dates_content:
                results.update(dates_content)

            if not results:
                results = dates_url.union(dates_content)

        results = list(results)

        return results

if __name__ == '__main__':
    import urllib2

    if len(sys.argv) == 1:
        url = "http://www.cnn.com/2010/US/05/20/gulf.oil.spill/index.html?hpt=T2"
    else:
        url = ' '.join(sys.argv[1:])
    content = urllib2.urlopen(url).read()

    tu = DateMiner()
    print tu.coerce_dates(url, content)