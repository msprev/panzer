from setuptools import setup

setup(name='panzer',
      version='0.9.1b',
      description='pandoc with style',
      long_description=open('README.rst').read(),
      url='https://github.com/msprev/panzer',
      author='Mark Sprevak',
      author_email='mark.sprevak@ed.ac.uk',
      license='LICENSE.txt',
      packages=['panzer'],
      install_requires=['pandocfilters'],
      include_package_data=True,
      keywords=['pandoc'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3',
          'Topic :: Text Processing'
        ],
      entry_points = {
          'console_scripts': [
              'panzer = panzer.panzer:main'
          ]
        },
      zip_safe=False)
