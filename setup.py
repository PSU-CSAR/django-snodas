#!/usr/bin/env python
from setuptools import setup, find_packages


PYTHON_REQUIREMENTS = '>=3.10'


def get_readme():
    with open('README.md', 'r') as r:
        return r.read()


def get_version():
    with open('VERSION.txt', 'r') as v:
        return v.read().strip()


def main():
    readme = get_readme()
    version = get_version()
    download_url = (
        'https://github.com/PSU-CSAR/django-snodas/tarball/{}'.format(version)
    )

    setup(
        name='django-snodas',
        #packages=find_packages(),
        py_modules=['manage'],
        version=version,
        description=(
            'Interface to SNODAS daily and aggregate rasters '
            'as a tile service and for analytical functions.'
        ),
        long_description=readme,
        author=('Portland State University '
                'Center for Spatial Analysis and Research'),
        author_email='jkeifer@pdx.edu',
        url='https://github.com/PSU-CSAR/django-snodas',
        download_url=download_url,
        entry_points='''
            [console_scripts]
            snodas=manage:main
        ''',
        python_requires=PYTHON_REQUIREMENTS,
        install_requires=[
            'psycopg2-binary~=2.9.3',
            'Django~=4.0',
            'django-split-settings~=1.1',
            'pyyaml~=6.0',
            'django-cors-headers~=3.13',
            'sqlparse~=0.4.2',
        ],
        extras_require={
        },
        dependency_links=[
        ],
        license='',
    )


if __name__ == '__main__':
    main()
