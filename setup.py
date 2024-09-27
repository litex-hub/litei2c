#!/usr/bin/env python3

from setuptools import setup
from setuptools import find_packages


setup(
    name                 = "litei2c",
    description          = "Small footprint and configurable I2C core",
    author               = "LiteI2C Developers",
    url                  = "https://github.com/litex-hub",
    download_url         = "https://github.com/litex-hub/litei2c",
    test_suite           = "test",
    license              = "BSD",
    python_requires      = "~=3.7",
    packages             = find_packages(exclude=("test*", "sim*", "doc*", "examples*")),
    include_package_data = True,
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
