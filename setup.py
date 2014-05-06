from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='panzer',
      version='0.9b',
      description='pandoc with styles',
      long_description=readme(),
      url='https://github.com/msprev/panzer',
      author='Mark Sprevak',
      author_email='mark.sprevak@ed.ac.uk',
      license='BSD3',
      packages=['panzer'],
      install_requires=['pandocfilters'],
      include_package_data=True,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
          'Topic :: Text Processing'
        ],
      entry_points = {
          'console_scripts': [
              'panzer = panzer.panzer:main'
          ]
        },
      zip_safe=False)
