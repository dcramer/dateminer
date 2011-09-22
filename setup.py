import os.path
from setuptools import setup, find_packages

setup(name='dateminer',
    version='0.2',
    author='DISQUS',
    author_email='opensource@disqus.com',
    maintainer='David Cramer',
    maintainer_email='dcramer@gmail.com',
    description='Extract dates from webpages',
    url='http://github.com/dcramer/dateminer',
    license='Apache License 2.0',
    install_requires=[
        'lxml',
    ],
    tests_require=[
        'unittest2',
    ],
    test_suite='unittest2.collector',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
