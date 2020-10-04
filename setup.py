from setuptools import setup, find_packages

from os import path
import re

here = path.abspath(path.dirname(__file__))

pkgname = 'pymcumgr'
src_dir = 'src'


def find_version(*file_paths):
    with open(path.join(here, *file_paths), encoding='utf-8') as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')

def long_description(*file_paths):
    with open(path.join(here, *file_paths), encoding='utf-8') as f:
        return f.read()


setup(
   name=pkgname,
   version=find_version(src_dir, pkgname, '__init__.py'),
   description=pkgname + ' helps you manage remote devices',
   author='Matthias Wauer',
   author_email='matthiaswauer@gmail.com',
   packages=find_packages(where=src_dir),
   package_dir={
      '': src_dir,
   },
   url='pymcumgr.somewhere',
   install_requires=[
      'pydbusbluez',
      'cbor==1.0.0',
   ], #external packages as dependencies
   license='MIT',
   classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Operating System :: Linux',
      'Programming Language :: Python :: 3.5',
      'Programming Language :: Python :: 3.6',
      'Programming Language :: Python :: 3.7',
      'Programming Language :: Python :: 3.8',
      'Programming Language :: Python :: 3.9',
      'Topic :: Software Development :: Testing',
   ],
   python_requires='>=3.5',
   entry_points={
      'console_scripts': [
         'pymcumgr = {}.pymcumgr:main'.format(pkgname),
      ]
   }
)
