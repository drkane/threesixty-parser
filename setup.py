from setuptools import setup

setup(
    name="threesixtygiving",
    packages=["threesixty"],
    version="0.0.3",
    author="David Kane david@dkane.net",
    include_package_data=True,
    license="MIT",
    description="A class to help use threesixtygiving data",
    install_requires=[
        "requests==2.19.1",
        "jsonref==0.2",
        "jsonschema==2.6.0",
        "flattentool==0.5.0",
    ]
)
