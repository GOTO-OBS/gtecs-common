"""Setup script for the gtecs-common package."""
from setuptools import find_namespace_packages, setup


setup(name='gtecs-common',
    version='0',
    description='G-TeCS common package',
    url='http://github.com/GOTO-OBS/gtecs-common',
    author='Martin Dyer',
    author_email='martin.dyer@sheffield.ac.uk',
    install_requires=[
        'slack_sdk>=3.20.1',
        'configobj',
        'fabric',
        'pid',
    ],
    extras_require={
        'db': [
            # Optional dependencies for database support
            'psycopg2',
            'sqlalchemy>=2',
        ]
    },
    packages=find_namespace_packages(include=['gtecs*']),
    zip_safe=False,
    )
