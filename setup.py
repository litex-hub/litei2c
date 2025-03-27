#!/usr/bin/env python3

from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as fp:
     long_description = fp.read()

setup(
    name                 = "litei2c",
    version              = "2024.12",
    description          = "Small footprint and configurable I2C core",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author               = "LiteI2C Developers",
    url                  = "https://github.com/litex-hub",
    download_url         = "https://github.com/litex-hub/litei2c",
    test_suite           = "test",
    license              = "BSD",
    python_requires      = "~=3.7",
    packages             = find_packages(exclude=("test*", "sim*", "doc*", "examples*")),
    include_package_data = True,
    install_requires=["migen", "litex"],
    extras_require={"develop": ["setuptools"]},
    keywords             = "HDL ASIC FPGA hardware design",
    classifiers          = [
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Environment :: Console",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
)
