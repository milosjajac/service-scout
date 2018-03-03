import os
from setuptools import setup

DIR = os.path.dirname(os.path.realpath(__file__))

setup(
    name='service-scout',
    version='1.0.0',
    author='Milos Jajac',
    install_requires=open('%s/requirements.txt' % DIR).readlines(),
    entry_points={
        'console_scripts': [
            'service_scout = scout.main'
        ]
    }
)
