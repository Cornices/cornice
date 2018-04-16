# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
import os
import sys
import pkg_resources
try:
    import mozilla_sphinx_theme
except ImportError:
    print('please install the \'mozilla-sphinx-theme\' distribution')

sys.path.insert(0, os.path.abspath('../..'))  # include cornice from the source
extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Cornice'
this_year = datetime.datetime.now().year
copyright = u'2011-{}, Mozilla Services'.format(this_year)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version =  pkg_resources.get_distribution('cornice').version
# The full version, including alpha/beta/rc tags.
release = version

exclude_patterns = []

html_theme_path = [os.path.dirname(mozilla_sphinx_theme.__file__)]

html_theme = 'mozilla'
html_static_path = ['_static']
htmlhelp_basename = 'Cornicedoc'

latex_documents = [
  ('index', 'Cornice.tex', u'Cornice Documentation',
   u'Mozilla Services', 'manual'),
]

man_pages = [
    ('index', 'cornice', u'Cornice Documentation',
     [u'Mozilla Services'], 1)
]
