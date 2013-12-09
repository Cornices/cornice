# flake8: noqa
# -*- coding: utf-8 -*-
import sys, os
try:
    import mozilla_sphinx_theme
except ImportError:
    print("please install the 'mozilla-sphinx-theme' distribution")

sys.path.insert(0, os.path.abspath("../.."))  # include cornice from the source
extensions = ['cornice.ext.sphinxext', 'sphinx.ext.autodoc']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Cornice'
copyright = u'2011, Mozilla Services'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.17'
# The full version, including alpha/beta/rc tags.
release = '0.17'

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
