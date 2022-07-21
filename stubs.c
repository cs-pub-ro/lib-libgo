/* SPDX-License-Identifier: BSD-3-Clause */
/*
 *
 * Authors: Charalampos Mainas <charalampos.mainas@neclab.eu>
 *
 *
 * Copyright (c) 2019, NEC Europe Ltd., NEC Corporation. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <stdio.h>
#include <errno.h>
#include <sys/statfs.h>
#include <sys/stat.h>
#include <uk/essentials.h>
#include <fcntl.h>
#include <stdlib.h>

int klogctl(int type __unused, char *bufp __unused, int len __unused)
{
	errno = ENOSYS;
	return -1;
}

ssize_t sendfile64(int out_fd __unused, int in_fd __unused,
		   off_t *offset __unused, size_t count __unused)
{
	errno = ENOSYS;
	return -1;
}

int posix_openpt(int flags __unused)
{
	errno = ENOSYS;
	return -1;
}

int unlockpt(int fd __unused)
{
	errno = ENOSYS;
	return -1;
}

int sigaltstack(const void *nss __unused, const void *oss __unused)
{
	return 0;
}

int madvise(void *addr __unused, size_t length __unused, int advice __unused)
{
	return 0;
}

int mlock(const void *addr __unused, size_t len __unused)
{
	return 0;
}

int munlock(const void *addr __unused, size_t len __unused)
{
	return 0;
}

int mlockall(int flags __unused)
{
	return 0;
}

int munlockall(void)
{
	return 0;
}

int msync(void *addr __unused, size_t length __unused, int flags __unused)
{
	return 0;
}

long ptrace(int request __unused, pid_t pid __unused, void *addr __unused,
	    void *data __unused)
{
	errno = ENOSYS;
	return -1;
}

int reboot(int cmd __unused)
{
	errno = EPERM;
	return -1;
}

int iopl(int level __unused)
{
	return 0;
}

int ioperm(unsigned long from __unused, unsigned long num __unused,
	   int turn_on __unused)
{
	return 0;
}

int pivot_root(const char *new_root __unused, const char *put_old __unused)
{
	errno = EPERM;
	return -1;
}

int adjtimex(void *buf __unused)
{
	errno = EPERM;
	return -1;
}

int acct(const char *filename __unused)
{
	return 0;
}

int setdomainname(const char *name __unused, size_t len __unused)
{
	errno = EPERM;
	return -1;
}

int settimeofday(const struct timeval *tv __unused,
		 const struct timezone *tz __unused)
{
	errno = EPERM;
	return -1;
}
