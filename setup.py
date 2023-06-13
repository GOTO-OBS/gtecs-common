"""Setup script for the gtecs-common package."""
from setuptools import find_namespace_packages, setup


REQUIRES = ['requests',
            'configobj',
            'fabric',
            'pid',
            'pymysql',
            # 'psycopg2',  # remove as requirement as it requires postgresql to be installed
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
