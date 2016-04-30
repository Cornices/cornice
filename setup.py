import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = ['pyramid',  'simplejson']

entry_points = """\
[paste.paster_create_template]
cornice=cornice.scaffolds:CorniceTemplate
cornice_swagger=cornice.scaffolds:CorniceSwaggerTemplate
[pyramid.scaffold]
cornice=cornice.scaffolds:CorniceTemplate
cornice_swagger=cornice.scaffolds:CorniceSwaggerTemplate
"""

package_data = {
    "cornice.scaffolds": [
        "cornice/*.*",
        "cornice/+package+/*.*"]}

setup(name='cornice',
      version='1.3.0.dev0',
      description='Define Web Services in Pyramid.',
      long_description=README + '\n\n' + CHANGES,
      license='MPLv2.0',
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Framework :: Pylons",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)", ],
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
      paster_plugins=['pyramid'])
