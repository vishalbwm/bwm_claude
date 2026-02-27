from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="bwm_claude",
    version="0.0.1",
    description="BWM Claude - Custom overrides and automation for Banaraswala Wire Mesh",
    author="Banaraswala Wire Mesh P Limited",
    author_email="vishal@banaraswala.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
