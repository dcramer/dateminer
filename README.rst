dateminer is a Python port of John Muellerleile's dateminer Java library:

  https://github.com/jrecursive/date_miner

It gives you a *best guess* at the creation date of an article (webpage) based on the URL and content of that page.

Usage
=====

>>> from dateminer import guess_date
>>> date = guess_date(url, html_content)