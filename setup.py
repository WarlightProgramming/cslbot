from distutils.core import setup
setup(
    name = 'wl_cslbot',
    packages = ['wl_cslbot'],
    install_requires = [
        'sheetDB==0.1.1',
        'wl_parsers==0.1.1',
        'wl_api==0.1.4',
        'skills==0.3.0',
    ],
    version = '0.0.1',
    description = 'a bot to automate Warlight leagues',
    author = 'knyte',
    author_email = 'galactaknyte@gmail.com',
    url = 'https://github.com/knyte/cslbot',
    keywords = ['Google Sheets', 'Warlight', 'CSL framework'],
    classifiers = [],
)
