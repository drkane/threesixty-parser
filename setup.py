from setuptools import setup

setup(
    name="threesixtygiving",
    packages=["threesixty"],
    version="0.0.2",
    author="David Kane david@dkane.net",
    include_package_data=True,
    license="MIT",
    description="A class to help use threesixtygiving data",
    install_requires=[
        "requests==2.19.1",
        "jsonref==0.2",
        "jsonschema==2.6.0",
        "-e git+https://github.com/OpenDataServices/flatten-tool.git@bb485e6390ba5bed527546f8493a7a0b727fb354#egg=flattentool",
    ]
)
