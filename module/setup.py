from setuptools import setup, find_packages


from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name="kubernetes-user",
    version="0.0.3",
    author="Joe Jasinski",
    description="A package for creating kubernetes users.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/JoeJasinski/k8s_user",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "kubernetes",
        "cryptography",
        "pyyaml",
    ],
    extras_require={
        "test":  ["pytest", "pytest-cov", "black", "coverage"],
    },
    entry_points={
        "console_scripts": [
            "k8s_user = k8s_user.__main__:main",
        ],
    }
)