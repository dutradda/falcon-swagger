# MIT License

# Copyright (c) 2016 Diogo Dutra

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from version import VERSION
from setuptools import setup, find_packages, Extension
import glob
import imp
import io
import os
from os import path
import sys

MYDIR = path.abspath(os.path.dirname(__file__))
JYTHON = 'java' in sys.platform

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

if PYPY or JYTHON:
    CYTHON = False
else:
    try:
        from Cython.Distutils import build_ext
        CYTHON = True
    except ImportError:
        # TODO(kgriffs): pip now ignores all output, so the user
        # may not see this message. See also:
        #
        #   https://github.com/pypa/pip/issues/2732
        #
        print('\nNOTE: Cython not installed. '
              'Falcon will still work fine, but may run '
              'a bit slower.\n')
        CYTHON = False

if CYTHON:
    def list_modules(dirname):
        filenames = glob.glob(path.join(dirname, '*.py'))

        module_names = []
        for name in filenames:
            module, ext = path.splitext(path.basename(name))
            if module != '__init__' and module != 'constants':
                module_names.append(module)

        return module_names

    package_names = ['falconswagger', 'falconswagger.models']
    ext_modules = [
        Extension(
            package + '.' + module,
            [path.join(*(package.split('.') + [module + '.py']))]
        )
        for package in package_names
        for module in list_modules(path.join(MYDIR, *package.split('.')))
    ]

    cmdclass = {'build_ext': build_ext}

else:
    cmdclass = {}
    ext_modules = []


long_description = ''
with open('README.md') as readme:
    long_description = readme.read()


install_requires = []
with open('requirements.txt') as requirements:
    install_requires = requirements.readlines()


tests_require = []
with open('requirements-dev.txt') as requirements_dev:
    tests_require = requirements_dev.readlines()


setup(
    name='falcon-swagger',
    packages=find_packages('.'),
    include_package_data=True,
    version=VERSION,
    description='A Falcon Framework extension featuring Swagger, SQLAlchemy and Redis',
    long_description=long_description,
    author='Diogo Dutra',
    author_email='dutradda@gmail.com',
    url='https://github.com/dutradda/falcon-swagger',
    download_url='http://github.com/dutradda/falcon-swagger/archive/master.zip',
    license='MIT',
    keywords='falcon framework swagger openapi sqlalchemy redis crud',
    setup_requires=[
        'pytest-runner==2.9',
        'setuptools==28.3.0'
    ],
    tests_require=tests_require,
    install_requires=install_requires,
    cmdclass=cmdclass,
    ext_modules=ext_modules,
    classifiers=[
    	'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
