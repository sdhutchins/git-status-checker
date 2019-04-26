from setuptools import setup, find_packages

# References and tools:
# * Cookiecutter
# * https://packaging.python.org/
# * https://setuptools.readthedocs.io
# * https://www.youtube.com/watch?v=4fzAMdLKC5k&t=1228s

# Notes:
# * You can use a setup.cfg file, c.f. https://setuptools.readthedocs.io/en/latest/setuptools.html
# * http://setuptools.readthedocs.io/en/latest/setuptools.html#new-and-changed-setup-keywords
# * http://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files
# * https://github.com/pypa/sampleproject/issues/30
# * Do not use the old `data_files` keyword, it is very hard to get right. Use MANIFEST.in + include_package_data.
#   * Using `package_data` should generally also be avoided in favor of MANIFEST.in.
# Remember to clear the build/ and *.egg-info/*.wheel-info directories if you get any unexpected build behavior.

setup(
    name='git-status-checker',
    description='Check git repositories for uncommitted or unpushed changes.',
    long_description=open('README.md').read(),
    version='1.1.2',
    url='https://github.com/vallenderlab/git-status-checker',
    license='GNU General Public License v3 (GPLv3)',
    author='Rasmus Scholer Sorensen <rasmusscholer@gmail.com>, Shaurita Hutchins <sdhutchins@outlook.com>',
    packages=find_packages(exclude=['docs', 'tests']),
    entry_points={
        'console_scripts': [
            'git-status-checker=git_status_checker.git_status_checker:main',
        ],
    },
    install_requires=['pyyaml','logzero',],
    keywords=["Git", "Version control", "Development tools",],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',

        'Operating System :: MacOS',
        'Operating System :: Microsoft',
        'Operating System :: POSIX :: Linux',
    ],
    project_urls={
        'Documentation': '',
        'Bug Reports': 'https://github.com/vallenderlab/git-status-checker/issues',
        'Source': 'https://github.com/vallenderlab/git-status-checker',
    },
)
