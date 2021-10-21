#!/usr/bin/env python3
from setuptools import find_packages, setup
from pathlib import Path


def get_pip_deps():
    dependency_links = []
    install_requires = [
        "streamlit",
        "streamlit_webrtc==0.31.0",
        "aiortc==1.2.1",
        "numpy==1.21.2",
        "matplotlib==3.4.3",
        "pydub==0.25.1",
        "streamlit==1.0.0",
        "typing_extensions==3.10.0.2",
        "numpy",
        "lhotse",
    ]
    return install_requires, dependency_links


project_dir = Path(__file__).parent
install_requires, dependency_links = get_pip_deps()

setup(
    name="speechwoz",
    version="0.1",
    python_requires=">=3.6.0",
    description="Previewing Multiwoz and recording its reading",
    author="Ondrej Platek",
    packages=find_packages(),
    install_requires=install_requires,
    dependency_links=dependency_links,
    extras_require={"test": ["pytest"]},
    enty_points={
        "console_scripts": [
            "woz = speechwoz.cli:woz",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: Science/Research",
        "Operating System :: POSIX :: Linux",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
