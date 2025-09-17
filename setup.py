from setuptools import setup, find_packages

setup(
    name="mobaxtermbutbetter",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "paramiko",
        "PyQt5",
        "pyte>=0.8.1"
    ],
)