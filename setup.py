from setuptools import setup, find_packages

setup(
    name="hiptender",
    version="0.1",
    packages=find_packages(),
    setup_requires=["python-dateutil"],
    install_requires=[
	"configobj",
	"croniter",
	"crontab",
        "gevent",
	#"hipchat",
	"python-crontab",
	"python-dateutil",
	"pytz",
    ],
    dependency_links=[
	'git+https://github.com/samv/python-hipchat@master#egg=hipchat'
    ],
    entry_points={
        'console_scripts': [
            'hiptender = hiptender:main',
        ],
    },
    author="Sam Vilain",
    author_email="sam@datapad.io",
    description="A bot for running daily standup meetings over HipChat",
    license="GPL3",
    keywords="hipchat stand-up agile scrum status",
)
