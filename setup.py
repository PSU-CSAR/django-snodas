#!/usr/bin/env python
from setuptools import setup, find_packages


PYTHON_REQUIREMENTS = '>=2.7.11,<3.0'


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
            'psycopg2>=2.7.1',
            'Django>=1.11',
            'djangorestframework>=3.6.2',
            'GDAL>=2.1.0',
            'djangorestframework-gis>=0.11.0',
            'django-split-settings>=0.2.4',
#            'pyyaml>=3.12',
#            'six>=1.10.0',
        ],
        extras_require={
            'CORS': ['django-cors-headers>=2.0.2'],
            'DEV': [
                'django-extensions>=1.4.9',
                'django-debug-toolbar>=1.7',
                'mock>=2.0.0',
            ],
        },
        dependency_links=[
        ],
        license='',
    )


if __name__ == '__main__':
    main()
