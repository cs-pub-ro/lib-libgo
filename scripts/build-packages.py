import re
import os
import shutil
from collections import OrderedDict

def extract_version_from_buildcfg(path):
	with open(path, 'r') as f:
		for line in f.readlines():
			if line.startswith('const version = '):
				return line[17:-2]

def dep_file_to_config_opt(path):
	return 'LIBGO_PKG_' + path[:-2].replace('/','_').replace('.','_').upper()

re_gccgo = re.compile(r'^libtool: compile:.*gccgo\s')
re_gcc   = re.compile(r'^libtool: compile:.*xgcc.*/libgo/')
re_gosrc = re.compile(r'\s([a-z0-9_\/\-\.]+\.go)')
re_csrc  = re.compile(r'-c\s([a-z0-9_\/\-\.]+\.(?:S|c))')
re_out   = re.compile(r'\s-o\s([a-z0-9_\/\-\.]+)')
re_flags = re.compile(r'\s(-fgo-[a-z0-9_\/\-\.=]+)')

build_cmds = """
	$(call verbose_cmd,GO,libgo: $(notdir $@), cd $(LIBGO_EXTRACTED) && \\
	mkdir -p $(dir $@) && \\
	$(GOC) $(LIBGO_GOFLAGS) -c {}-fgo-pkgpath=$(subst $(LIBGO_BUILD)/,,$(@:.o=)) $(filter %.go,$^) -o $@ && \\
	objcopy -j .go_export $@ $(@:.o=.gox))
"""

packages_uk_header = """# This file has been auto-generated for {}.
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

packages_uk_footer = """
LIBGO_CLEAN += $(LIBGO_OBJS-y) $(LIBGO_OBJS-y:.o=.gox)
"""

packages_config_entry = """
config {}
	bool \"{}\"
	default {}
"""

build_log	   = './build.log'
build_dir	   = './x86_64-pc-linux-gnu/'
base_dir	   = os.path.dirname(__file__)
libgo_dir	   = base_dir + '/libgo'
packages_uk	   = libgo_dir + '/packages.uk'
sources_uk	   = libgo_dir + '/sources.uk'
packages_config_uk = libgo_dir + '/packages_config.uk'

print('Build directory: {}'.format(build_dir))
print('Target: {}'.format(base_dir))

pkgs = {}
srcs = []
pkg_text = ''
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

		# Extract dependency information
		# We parse the *.lo.dep file from the build for this
		dep_path = build_dir + 'libgo/' + obj[:-1] + 'lo.dep'

		deps_text = ''
		with open(dep_path, 'r') as depf:
			dep_line = depf.readline().strip()
			dep_files = dep_line.split(' ')
			for dep_file in dep_files:
				if dep_file.endswith('.gox'):
					dep_obj =  dep_file[:-3] + 'o'
					deps_text += ' $(LIBGO_BUILD)/' + dep_obj
					pkgs[obj].append(dep_obj)

		# Start constructing the build rule for the package
		res_line = '$(LIBGO_BUILD)/' + obj + ':'

		matches = re_gosrc.findall(line)
		for source_file in matches:
			p = source_file.find('/libgo/')
			if p < 0:
				# This is probably one of the files that are generated.
				# We copy these files to the libgo folder in lib-libgo
				if source_file.find('/') == -1:
					print('INFO: Importing generated file "{}"'.format(source_file))
					path = build_dir + '/libgo/' + source_file

					# This file contains version information. Extract them.
					if source_file == 'buildcfg.go':
						gcc_version = extract_version_from_buildcfg(path)

					#shutil.copy(path, generated_dir + '/' + source_file)
					res_line += ' $(LIBGO_BASE)/libgo/' + source_file
					continue

				print('WARN: "{}" has unknown path. Ignoring.'.format(source_file))
				continue

			res_line += ' $(LIBGO_EXTRACTED)/' + source_file[p + 7:]

		# Check for additional flags
		res_flags = ''
		matches = re_flags.findall(line)
		for flag in matches:
			if flag.startswith('-fgo-pkgpath'):
				continue
			res_flags += flag + ' '

		if res_flags != '':
			print('INFO: Using additional flags "{}" for "{}"'.format(obj, res_flags))

		# Add package to package makefile
		pkg_text += res_line + deps_text
		pkg_text += build_cmds.format(res_flags)

pkg_text = packages_uk_header.format(gcc_version, os.path.basename(__file__)) + pkg_text

pkg_text += '\n'
for (obj, deps) in pkgs.items():
	pkg_text += 'LIBGO_OBJS-$(CONFIG_{}) += {}\n'.format(dep_file_to_config_opt(obj), '$(LIBGO_BUILD)/' + obj)
	if len(deps) == 0:
		print('INFO: "{}" is an optional package'.format(obj[:-2]))

pkg_text += packages_uk_footer

# Write packages.uk
with open(packages_uk, 'w') as pf:
	pf.write(pkg_text)

# Write packages_config.uk
pcf_text = ''
for (obj, deps) in OrderedDict(sorted(pkgs.items())).items():
	pcf_text += packages_config_entry.format(dep_file_to_config_opt(obj),
		obj[:-2], "n")
	for dep in deps:
		pcf_text += "\tselect " + dep_file_to_config_opt(dep) + "\n"

with open(packages_config_uk, 'w') as pcf:
	pcf.write(pcf_text)

# Write sources.uk
srcs.sort()
with open(sources_uk, 'w') as sf:
	for cfile in srcs:
		sf.write('LIBGO_SRCS-y += $(LIBGO_EXTRACTED)/' + cfile + '\n')
