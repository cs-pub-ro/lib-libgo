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

	return json_text

def vgolib(libname):
	return libname.replace('.','_').replace('/','_').replace('-','_').upper()

# Constants
MK_ADDGOLIB = '$(eval $(call addgolib,{}))\n'
MK_SRCS     = '{}_SRCS += {}\n'
MK_DEPS     = '{}_DEPS += {}\n'

parser = argparse.ArgumentParser(description='Generates a makefile ')
parser.add_argument('-v', default=False, action='store_true',
		    help='Print executed commands')
parser.add_argument('-o', dest='out', default=None,
		    help='Output path')
group = parser.add_mutually_exclusive_group(required=False)
group.add_argument('-j', dest='json', default=False, action='store_true',
		   help='Dump JSON from go list instead of generating a Makefile')
group.add_argument('-s', dest='std', default=False, action='store_true',
		   help='Dump dependencies on standard packages instead of generating a Makefile')
group.add_argument('-c', dest='config', default=False, action='store_true',
		   help='Generate config entries for dependencies on standard packages instead of generating a Makefile')
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

# Load std packages
base_dir	= os.path.dirname(__file__) + '/..'
libgo_dir	= base_dir + '/libgo'
std_packages	= libgo_dir + '/std_packages'

std_pkgs = {}
with open(std_packages, 'r') as f:
	lines = f.readlines()
	for line in lines:
		pkgs = line.rstrip().split(' ')
		std_pkgs[pkgs[0]] = pkgs[1:] if len(pkgs) > 1 else []

# We start with the entrance file(s) and request information on all
# dependencies for these files using `go list`. This will implicitly download
# all dependencies and we receive lists of files necessary to build the
# respective packages
out = ''

try:
	build_info = go_list(opt.lib_dir, opt.files)
	if opt.json:
		out = build_info
	else:
		build_info = json.loads(build_info)
		std_deps = []
		for pkg in build_info['packages']:
			if pkg['ImportPath'] in std_pkgs:
				std_deps.append(pkg['ImportPath'])
				continue

			if 'Standard' in pkg:
				continue

			if opt.std or opt.config:
				continue

			# Check if this is the package that was specified with
			# the entrance files. In that case, add all dependencies
			if ('Target' in pkg or (('ImportPath' in pkg and
			(pkg['ImportPath'] == opt.lib_name or
			pkg['ImportPath'] == 'command-line-arguments')))):
				if 'Deps' in pkg:
					for dep in pkg['Deps']:
						if dep in std_pkgs:
							continue

						out += MK_DEPS.format(libprefix, dep)

				continue

			# This is a some dependency package. Create a new GO
			# library registration for the package and add the
			# source files to it
			pkglibprefix = vgolib(pkg['ImportPath'])
			out += MK_ADDGOLIB.format(pkg['ImportPath'])

			files = pkg['GoFiles'] if 'GoFiles' in pkg else []
			files.extend(pkg['CFiles'] if 'CFiles' in pkg else [])

			for f in files:
				path = pkg['Dir'] + '/' + f
				if not os.path.exists(path):
					raise FileNotFoundError(errno.ENOENT,
						os.strerror(errno.ENOENT), path)

				out += MK_SRCS.format(pkglibprefix, path)

			# Add the package's dependencies
			if 'Deps' in pkg:
				for dep in pkg['Deps']:
					if dep in std_pkgs:
						continue

					out += MK_DEPS.format(pkglibprefix, dep)

		if opt.std:
			for pkg in std_deps:
				out += pkg + '\n'
		elif opt.config:
			for pkg in std_deps:
				out += '\tselect LIBGO_PKG_{}\n'.format(vgolib(pkg))

except Exception as e:
	logging.fatal(e.args[0])
	sys.exit(-1)

# Write the output either to stdout or the specified output file
if opt.out == None:
	print(out)
else:
	with open(opt.out, 'w') as f:
		f.write(out)
