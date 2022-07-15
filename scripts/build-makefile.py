#!/usr/bin/env python3
#
# Copyright (c) 2022, Karlsruhe Institute of Technology (KIT)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

import argparse
import os
import json
import logging
import subprocess
import errno
import sys

def go_list(lib_dir, files):
	args = ['go', 'list', '--json', '-a', '--compiler=gccgo', '--deps']
	args.extend(files)
	logging.debug(' '.join(args))

	env = os.environ.copy()
	env['LD_LIBRARY_PATH'] = '/usr/lib64/'
	#env['GOPATH'] = opt.build_dir

	p = subprocess.run(args, stdout=subprocess.PIPE,
			   stderr=subprocess.PIPE, cwd=lib_dir, env=env)
	if p.returncode != 0:
		raise Exception('go list failed ({}):\n{}'.format(p.returncode,
			p.stderr.decode('UTF-8')))

	# The output from go list produces only valid json for each package but
	# otherwise just concatenates the output. We wrap these individual
	# json outputs with a top json structures that creates an array
	json_text = '{ "packages" : ['\
		+ p.stdout.decode('UTF-8').replace('}\n{','},{')\
		+ '] }'

	return json.loads(json_text)

def vgolib(libname):
	return libname.replace('.','_').replace('/','_').upper()

def is_standard(libname, build_info):
	for pkg in build_info['packages']:
		if not 'ImportPath' in pkg:
			continue

		if libname == pkg['ImportPath']:
			return ('Standard' in pkg)

	return False

# Constants
MK_ADDGOLIB = '$(eval $(call addgolib,{}))\n'
MK_SRCS     = '{}_SRCS += {}\n'
MK_DEPS     = '{}_DEPS += {}\n'

parser = argparse.ArgumentParser(description='Generates a makefile ')
parser.add_argument('-v', default=False, action='store_true',
		    help='Print executed commands')
parser.add_argument('-o', dest='out', default=None,
		    help='Output path')
parser.add_argument('lib_name',
		    help='Name of the library')
parser.add_argument('lib_dir',
		    help='Source directory of the library')
parser.add_argument('files', nargs='+',
		    help='Entrance *.go files of the library')
opt = parser.parse_args()

if opt.v:
	logging.basicConfig(level=logging.DEBUG)
else:
	logging.basicConfig(level=logging.INFO)

lib_dir = os.path.abspath(opt.lib_dir)
if not os.path.exists(lib_dir):
	parser.error('{} not found'.format(lib_dir))

libprefix = vgolib(opt.lib_name)

# We start with the entrance file(s) and request information on all
# dependencies for these files using `go list`. This will implicitly download
# all dependencies and we receive lists of files necessary to build the
# respective packages
build_info = go_list(opt.lib_dir, opt.files)

mk = ''
#std_pkgs = []
try:
	for pkg in build_info['packages']:
		# Standard packages are part of libgo and we don't need to
		# build them.
		if 'Standard' in pkg:
			#std_pkgs.append(pkg['ImportPath'])
			continue

		# Check if this is the package that was specified with the
		# entrance files. In that case, add all dependencies
		if ('Target' in pkg or (('ImportPath' in pkg and
		    (pkg['ImportPath'] == opt.lib_name or
		     pkg['ImportPath'] == 'command-line-arguments')))):
			if 'Deps' in pkg:
				for dep in pkg['Deps']:
					if is_standard(dep, build_info):
						continue

					mk += MK_DEPS.format(libprefix, dep)

			continue

		# This is a some dependency package. Create a new GO library
		# registration for the package and add the source files to it
		pkglibprefix = vgolib(pkg['ImportPath'])
		mk += MK_ADDGOLIB.format(pkg['ImportPath'])

		for f in pkg['GoFiles']:
			path = pkg['Dir'] + '/' + f
			if not os.path.exists(path):
				raise FileNotFoundError(errno.ENOENT,
					os.strerror(errno.ENOENT), path)

			mk += MK_SRCS.format(pkglibprefix, path)

		# TODO: Handle c-files

		# Add the package's dependencies
		if 'Deps' in pkg:
			for dep in pkg['Deps']:
				if is_standard(dep, build_info):
					continue

				mk += MK_DEPS.format(pkglibprefix, dep)

	# Write out Makefile
	if opt.out == None:
		print(mk)
	else:
		with open(opt.out, 'w') as f:
			f.write(mk)

except Exception as e:
	logging.fatal(e.args[0])
	sys.exit(-1)
