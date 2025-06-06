# G-TeCS common package

**G-TeCS** (*gee-teks*) is the GOTO Telescope Control System.

This package (`gtecs-common`) contains common functions and utilities that are used by other G-TeCS packages.

Note this module is Python3 only and has been developed for Linux, otherwise use at your own risk.

## Requirements

This package requires several Python modules, which should be included during installation.

Database support is optional, but if you want to use it, you will need to install `postgresql`
first, and then install this package with the optional `db` flag (see below).

This package doesn't require any other G-TeCS packages to be installed, but it itself is a requirement of several of them.

## Installation

Once you've downloaded or cloned the repository, in the base directory run:

    pip3 install . --user

If you want to install the package with database support, run:

    pip3 install .[db] --user

You should then be able to import the module from within Python.

## Testing

TODO

## Usage

TODO
