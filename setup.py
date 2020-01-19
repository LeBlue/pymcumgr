from setuptools import setup, find_packages

version = '0.1.0'
pkgname = 'pymcumgr'
src_dir = 'src'

setup(
   name=pkgname,
   version=version,
   description=pkgname + " helps you manage remote devices",
   author='Matthias Wauer',
   author_email='matthiaswauer@gmail.com',
   packages=find_packages(where=src_dir),
   package_dir={
      '': src_dir,
   },
   url='pydbusbluez.foobar',
   install_requires=[
      'pydbusbluez'
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
      'Topic :: Software Development :: Testing',
   ],
   entry_points={
      'console_scripts': [
         'pymcumgr = {}.pymcumgr:main'.format(pkgname),
      ]
   }
)
