import os
from setuptools import setup, find_packages

DIR = os.path.dirname(os.path.realpath(__file__))

setup(
    name='service-scout',
    version='1.0.0',
    author='Milos Jajac',
    packages=find_packages(),
    install_requires=open('%s/requirements.txt' % DIR).readlines(),
    entry_points={
        'console_scripts': [
            'service_scout = scout.scout:main'
        ]
    }
)
