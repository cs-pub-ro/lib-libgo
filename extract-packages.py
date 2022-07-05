import re
import os
import shutil

def extract_version_from_buildcfg(path):
	with open(path, 'r') as f:
		for line in f.readlines():
			if line.startswith('const version = '):
				return line[17:-2]


re_gccgo = re.compile(r'^libtool: compile:.*gccgo\s')
re_gcc = re.compile(r'^libtool: compile:.*xgcc.*/libgo/')
re_gosrc = re.compile(r'\s([a-z0-9_\/\-\.]+\.go)')
re_csrc = re.compile(r'-c\s([a-z0-9_\/\-\.]+\.(?:S|c))')
re_out = re.compile(r'\s-o\s([a-z0-9_\/\-\.]+)')
re_flags = re.compile(r'\s(-fgo-[a-z0-9_\/\-\.=]+)')

build_cmds = """
	$(call verbose_cmd,GO,libgo: $(notdir $@), cd $(LIBGO_EXTRACTED) && \\
	mkdir -p $(dir $@) && \\
	$(GOC) $(LIBGO_GOFLAGS) -c {}-fgo-pkgpath=$(subst $(LIBGO_BUILD)/,,$(@:.o=)) $^ -o $@ && \\
	objcopy -j .go_export $@ $(@:.o=.gox))
"""

header = """
# This file has been auto-generated for <$LIB_LIBGO_VERSION$>.
# To re-generate navigate to Unikraft application folder
#   $ make prepare
#   $ cd build/libgo/origin
#   $ mkdir gccbuild
#   $ cd gccbuild
#   $ ../gcc-$(LIBGCC_VERSION)/configure --disable-multilib --enable-languages=c,c++,go
#   $ make V=1 -j`nproc`| tee build.log
#   $ $(LIBGO_BASE)/extract_packages.py
#
"""

build_log = './build.log'
build_dir = './x86_64-pc-linux-gnu/'
target_dir = os.path.dirname(__file__)
generated_dir = target_dir + '/generated'
pkg_file = target_dir + '/packages.uk'
c_files = target_dir + '/sources.uk'

print('Build directory: {}'.format(build_dir))
print('Target: {}'.format(target_dir))

if os.path.exists(generated_dir):
	shutil.rmtree(generated_dir)

if os.path.exists(pkg_file):
	os.remove(pkg_file)

os.mkdir(generated_dir)

objs = []
cfiles = []
pkg_text = header
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

			cfiles.append(source_file[p + len('/libgo/'):] + '\n')
			continue

		# Check if this is a GO package needed for libgo
		matches = re_gccgo.findall(line)
		if len(matches) == 0:
			continue

		if line.find('-fPIC') >= 0:
			continue

		line = line[len(matches[0]):]

		matches = re_out.findall(line)
		if len(matches) != 1:
			continue

		obj = matches[0]

		# We do not need to build the cmd objs for libgo
		if obj.startswith('cmd/'):
			continue

		obj = '$(LIBGO_BUILD)/' + obj
		objs.append(obj)

		res_line = obj + ':'

		matches = re_gosrc.findall(line)
		for source_file in matches:
			p = source_file.find('/libgo/')
			if p < 0:
				# This is probably one of the files that are generated.
				# We copy these files to the generated folder in lib-libgo
				if source_file.find('/') == -1:
					print('INFO: Importing generated file "{}"'.format(source_file))
					path = build_dir + '/libgo/' + source_file

					# This file contains version information. Extract them.
					if source_file == 'buildcfg.go':
						pkg_text = pkg_text.replace('<$LIB_LIBGO_VERSION$>', extract_version_from_buildcfg(path))

					shutil.copy(path, generated_dir + '/' + source_file)
					res_line += ' $(LIBGO_BASE)/generated/' + source_file
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
		pkg_text += res_line
		pkg_text += build_cmds.format(res_flags)

	pkg_text += '\nLIBGO_OBJS += \\\n'
	for obj in objs:
		pkg_text += '\t' + obj + ' \\\n'

with open(pkg_file, 'w') as pf:
	pf.write(pkg_text)

with open(c_files, 'w') as sf:
	sf.writelines(cfiles)
