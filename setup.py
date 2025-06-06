"""Setup script for the gtecs-common package."""
from setuptools import find_namespace_packages, setup


REQUIRES = ['slack_sdk>=3.20.1',
            'configobj',
            'fabric',
            'pid',
            # 'psycopg2',  # requires postgresql to be installed, requirement for obs/alert only
            'sqlalchemy>=2',
            ]

setup(name='gtecs-common',
      version='0',
      description='G-TeCS common package',
      url='http://github.com/GOTO-OBS/gtecs-common',
      author='Martin Dyer',
      author_email='martin.dyer@sheffield.ac.uk',
      install_requires=REQUIRES,
      packages=find_namespace_packages(include=['gtecs*']),
      zip_safe=False,
      )
