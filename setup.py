from distutils.core import setup
from setuptools import setup

setup(
    name='memorial',
    version='1.0.1',
    url='https://github.com/arquivo/memorial',
    license='',
    description='Arquivo Memorial to serve preserved pages.',
    install_requires=[
        'flask',
        'bs4',
        'request',
        'uwsgi'
    ],
)
