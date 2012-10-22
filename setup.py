import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = ['pyramid',  'simplejson']
test_requires = requires + ['colander', 'unittest2', 'coverage',
                            'webtest', 'Sphinx', 'rxjson']

try:
    import importlib  # NOQA
except ImportError:
    test_requires.append('importlib')


entry_points = """\
[paste.paster_create_template]
cornice=cornice.scaffolds:CorniceTemplate
[pyramid.scaffold]
cornice=cornice.scaffolds:CorniceTemplate
"""

package_data = {
  "cornice.scaffolds":
    ["cornice/*.*",
     "cornice/+package+/*.*"]}

setup(name='cornice',
      version='0.11',
      description='Define Web Services in Pyramid.',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      entry_points=entry_points,
      author='Mozilla Services',
      author_email='services-dev@mozilla.org',
      url='https://github.com/mozilla-services/cornice',
      keywords='web pyramid pylons',
      packages=find_packages(),
      package_data=package_data,
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      test_suite="cornice.tests",
      paster_plugins=['pyramid'])
