import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="subscene-dl-sa3dany",
    version="0.1",
    author="Mohamed ElSaadany",
    author_email="mhsaadany@gmail.com",
    description="Download movie subtitles from subscene.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=["iso-639", "jellyfish", "requests"],
    entry_points={"console_scripts": ["subscene-dl = subscene.cli:main"]},
)
