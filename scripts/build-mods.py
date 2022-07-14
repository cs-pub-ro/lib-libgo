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
from subprocess import run, PIPE
import json

def go_list(entrance):
	args = ['go', 'list', '--json', '-a', '--compiler=gccgo', '--deps',
		entrance]

	env = os.environ.copy()
	env['LD_LIBRARY_PATH'] = '/usr/lib64/'
	#env['GOPATH'] = opt.build_dir

	p = run(args, stdout=PIPE, stderr=PIPE, env=env)
	if p.returncode != 0:
		raise Exception('go list -json {} failed ({}):\n{}'.format(
			entrance, p.returncode, p.stderr.decode('UTF-8')))

	# The output from go list produces only valid json for each package but
	# otherwise just concatenates the output. We wrap these individual
	# json outputs with a top json structures that creates an array
	json_text = '{ "packages" : ['\
		+ p.stdout.decode('UTF-8').replace('}\n{','},{')\
		+ '] }'

	return json.loads(json_text)

parser = argparse.ArgumentParser(description='TODO')
#parser.add_argument('build_dir',
#		    help='Path to the build directory of libgo')
parser.add_argument('entrance',
		    help='Primary *.go file of the project to build')
opt = parser.parse_args()

#opt.build_dir = os.path.abspath(opt.build_dir)
#if not os.path.exists(opt.build_dir):
#	parser.error('Build directory {} not found', opt.build_dir)

# We start with the entrance file(s) and request information on all
# dependencies for these files using `go list`. This will implicitly download
# all dependencies and we receive lists of files necessary to build the
# respective packages
build_info = go_list(opt.entrance)

pkgs = []
std_pkgs = []
for pkg in build_info['packages']:
	# Standard packages are part of libgo and we don't need to build them
	# However, we remember that we have this dependency
	if 'Standard' in pkg:
		std_pkgs.append(pkg['ImportPath'])
		continue

	# Target is the package that was specified with the entrance
	if 'Target' in pkg:
		print(["TARGET:", pkg['Target']])
		continue

	print(pkg['Root'])
	for f in pkg['GoFiles']:
		path = pkg['Dir'] + '/' + f
		if not os.path.exists(path):
			print("s")

	deps_text = ''
