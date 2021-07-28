from setuptools import setup
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='subscene-dl',
    version='0.3.0',
    description='Download movie subtitles from subscene.com',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='subscene, subtitles, cli',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],

    python_requires='>=3.6',
    packages=['subscene'],
    install_requires=[
        'colorama', 'iso-639', 'jellyfish', 'lxml', 'requests', 'xextract'
    ],
    extras_require={
        'dev': ['build', 'sphinx', 'twine'],
    },
    entry_points={
        'console_scripts': [
            'subscene-dl=subscene.cli:main'
        ]
    },
)
