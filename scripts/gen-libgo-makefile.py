import re
import os
import shutil
from collections import OrderedDict
import logging

def extract_version_from_buildcfg(path):
	with open(path, 'r') as f:
		for line in f.readlines():
			if line.startswith('const version = '):
				return line[17:-2]

def vgolib(libname):
	return libname.replace('.','_').replace('/','_').replace('-','_').upper()

re_gccgo = re.compile(r'^libtool: compile:.*gccgo\s')
re_gcc   = re.compile(r'^libtool: compile:.*xgcc.*/libgo/')
re_gosrc = re.compile(r'\s([a-z0-9_\/\-\.]+\.go)')
re_csrc  = re.compile(r'-c\s([a-z0-9_\/\-\.]+\.(?:S|c))')
re_out   = re.compile(r'\s-o\s([a-z0-9_\/\-\.]+)')
re_flags = re.compile(r'\s(-fgo-[a-z0-9_\/\-\.=]+)')

makefile_rt_header = """# This file has been auto-generated for {}.
# To re-generate navigate to Unikraft application folder
#   $ make prepare
#   $ cd build/libgo/origin
#   $ mkdir gccbuild
#   $ cd gccbuild
#   $ ../gcc-<GCC_VERSION>/configure --disable-multilib --enable-languages=c,c++,go
#   $ make V=1 -j`nproc`| tee build.log
#   $ $(LIBGO_BASE)/{}
#
"""

MK_ADDGOLIB = '$(eval $(call _addgolib,{},{}))\n'
MK_SRCS     = '{}_SRCS += {}\n'
MK_DEPS     = '{}_DEPS += {}\n'
MK_FLAGS    = '{}_FLAGS += {}\n'

build_log	= './build.log'
build_dir	= './x86_64-pc-linux-gnu/'
base_dir	= os.path.dirname(__file__) + '/..'
libgo_dir	= base_dir + '/libgo'
makefile_rt_uk	= libgo_dir + '/Makefile.runtime.uk'
makefile_nt_uk	= libgo_dir + '/Makefile.native.uk'
packages_idx	= libgo_dir + '/packages.idx'

logging.basicConfig(level=logging.INFO)

print('Build directory: {}'.format(build_dir))
print('Target: {}'.format(base_dir))

pkgs = {}
srcs = []
out = ''
gcc_version = 'unknown'
with open(build_log, 'r') as bl:
	for line in bl.readlines():
		# Check if this is a *.c file needed for libgo
		matches = re_gcc.findall(line)
		if len(matches) > 0:
			if line.find('-fPIC') >= 0:
				continue

			matches = re_csrc.findall(line)
			if len(matches) != 1:
				continue

			source_file = matches[0]
			p = source_file.find('/libgo/')
			if p < 0:
				continue

			source_file = source_file[p + len('/libgo/'):]

			# Sometimes we have the same base name twice.
			# This leads to overriding recipes in the Makefile.
			base_name = os.path.basename(source_file)
			for cfile in srcs:
				c = os.path.basename(cfile)
				if c == base_name:
					source_file += '|libgo'
					break

			srcs.append(source_file)
			continue

		# Check if this is a GO package needed for libgo
		matches = re_gccgo.findall(line)
		if len(matches) == 0:
			continue

		# We do not take the build command line for the dynamic library
		if line.find('-fPIC') >= 0:
			continue

		line = line[len(matches[0]):]

		# Extract object file name
		matches = re_out.findall(line)
		if len(matches) != 1:
			continue

		obj = matches[0]

		# We do not need to build the cmd objs for libgo
		if obj.startswith('cmd/'):
			continue

		# Ensure that we have an object (*.o) file here
		if not obj.endswith('.o'):
			continue

		pkgs[obj] = []
		pkg = obj[:-2]
		libprefix = vgolib(pkg)

		# Start constructing the build rule for the package
		out_lib = ''

		# Extract dependency and source file information
		# We parse the *.lo.dep file from the build for this
		# To make sure, we do a sanity check by also parsing the
		# build log
		src_files = re_gosrc.findall(line)

		dep_line = ''
		dep_path = build_dir + 'libgo/' + obj[:-1] + 'lo.dep'
		with open(dep_path, 'r') as depf:
			dep_line = depf.readline().strip()

		for dep in dep_line.split(' ')[1:]:
			if dep.endswith('.gox'):
				pkgs[obj].append(dep[:-3] + 'o')
				out_lib += MK_DEPS.format(libprefix, dep[:-4])
				continue

			if not dep in src_files:
				logging.warn('{} not found in build log for package {}'.format(dep, pkg))

			src_files.remove(dep)

			p = dep.find('/libgo/')
			if p >= 0:
				# A regular source file
				out_lib += MK_SRCS.format(libprefix, '$(LIBGO_EXTRACTED)/' + dep[p + 7:])
				continue

			# This is probably one of the files that are generated.
			# We copy these files to the libgo folder in lib-libgo
			if dep.find('/') == -1:
				logging.info('Importing generated file "{}"'.format(dep))
				path = build_dir + '/libgo/' + dep

				# This file contains version information. Extract them.
				if dep == 'buildcfg.go':
					gcc_version = extract_version_from_buildcfg(path)

				#shutil.copy(path, generated_dir + '/' + dep)
				out_lib += MK_SRCS.format(libprefix, '$(LIBGO_BASE)/libgo/' + dep)
				continue

			logging.warn('{} has unknown path. Ignoring.'.format(dep))

		if len(src_files) > 0:
			logging.warn('Additional sources in build log for package {}'.format(pkg))

		# Check for additional flags
		flags = ''
		matches = re_flags.findall(line)
		for flag in matches:
			if flag.startswith('-fgo-pkgpath'):
				continue

			flags += ' ' + flag
			logging.info('Additional flag for {}:{}'.format(pkg, flag))

		out += MK_ADDGOLIB.format(pkg, flags.strip()) + out_lib

out = makefile_rt_header.format(gcc_version, os.path.basename(__file__)) + out

# Write Makefile.runtime.uk
with open(makefile_rt_uk, 'w') as pf:
	pf.write(out)

# Write packages.idx
pidx_text = ''
for (obj, deps) in OrderedDict(sorted(pkgs.items())).items():
	pidx_text += obj[:-2]
	for dep in deps:
		pidx_text += ' ' + dep[:-2]
	pidx_text += '\n'

with open(packages_idx, 'w') as spf:
	spf.write(pidx_text)

# Write Makefile.native.uk
srcs.sort()
with open(makefile_nt_uk, 'w') as sf:
	for cfile in srcs:
		sf.write('LIBGO_SRCS-y += $(LIBGO_EXTRACTED)/' + cfile + '\n')
