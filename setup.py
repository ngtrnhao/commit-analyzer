from setuptools import setup, find_packages

setup(
    name="commit-analyzer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gitpython==3.1.41",
        "python-dotenv==1.0.1",
        "rich==13.7.0"
    ],
    entry_points={
        'console_scripts': [
            'commit=commit_analyzer.commit_analyzer:main',
        ],
    },
    author="Nguyen Truong Nhat Hao",
    author_email="nguyentruongnhathao1922@gmail.com",
    description="A smart tool that analyzes code changes and generates meaningful commit messages",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ngtrnhao/commit-analyzer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
    ],
    python_requires=">=3.7",
    keywords="git commit message analyzer semantic conventional-commits",
) 