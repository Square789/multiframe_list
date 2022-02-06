

import ast

from setuptools import setup

# Thanks: https://stackoverflow.com/questions/2058802/
# 	how-can-i-get-the-version-defined-in-setup-py-setuptools-in-my-package

__version__ = None
with open("multiframe_list/multiframe_list.py") as h:
	for line in h.readlines():
		if line.startswith("__version__"):
			__version__ = ast.parse(line).body[0].value.s
			break

if __version__ == None:
	raise SyntaxError("Version not found.")

with open("README.md") as h:
	long_desc = h.read()

setup(
	name = "multiframe_list",
	version = __version__,
	author = "Square789",
	description = "Tkinter widget to display data over multiple columns.",
	long_description = long_desc,
	long_description_content_type = "text/markdown",
	packages = ["multiframe_list"],
	classifiers = [
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python",
		"Topic :: Software Development :: User Interfaces",
		"Topic :: Software Development :: Libraries :: Python Modules"
	],
	url = "https://www.github.com/Square789/multiframe_list/",
)
