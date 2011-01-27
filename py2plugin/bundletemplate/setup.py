import os
import re
import sys
import distutils.sysconfig
import distutils.util

ARCH_BUILD_FLAGS = {
    'universal': {
        'target': '10.5',
        'cflags': '-isysroot /Developer/SDKs/MacOSX10.5.sdk -arch i386 -arch ppc -arch ppc64 -arch x86_64',
        'cc': 'gcc-4.2',
    },
    'ppc64': {
        'target': '10.5',
        'cflags': '-isysroot /Developer/SDKs/MacOSX10.5.sdk -arch x86_64',
        'cc': 'gcc-4.2',
    },
    'x86_64': {
        'target': '10.5',
        'cflags': '-isysroot / -arch x86_64',
        'cc': 'gcc-4.2',
    },
    'fat3': {
        'target': '10.5',
        'cflags': '-isysroot / -arch i386 -arch ppc -arch x86_64',
        'cc': 'gcc-4.2',
    },
    'intel': {
        'target': '10.5',
        'cflags': '-isysroot / -arch i386 -arch x86_64',
        'cc': 'gcc-4.2',
    },
    'i386': {
        'target': '10.3',
        'cflags': '-isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386',
        'cc': 'gcc-4.0',
    },
    'ppc': {
        'target': '10.3',
        'cflags': '-isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch ppc',
        'cc': 'gcc-4.0',
    },
    'fat': {
        'target': '10.3',
        'cflags': '-isysroot /Developer/SDKs/MacOSX10.4u.sdk -arch i386 -arch ppc',
        'cc': 'gcc-4.0',
    },
}


def main():
    basepath = os.path.dirname(__file__)
    builddir = os.path.join(basepath, 'prebuilt')
    if not os.path.exists(builddir):
        os.makedirs(builddir)
    src = os.path.join(basepath, 'src', 'main.m')

    cfg = distutils.sysconfig.get_config_vars()

    BASE_CFLAGS = cfg['CFLAGS']
    BASE_CFLAGS = BASE_CFLAGS.replace('-dynamic', '')
    BASE_CFLAGS += ' -bundle -framework Foundation -framework AppKit'
    while True:
        x = re.sub('-arch\s+\S+', '', BASE_CFLAGS)
        if x == BASE_CFLAGS:
            break
        BASE_CFLAGS=x

    while True:
        x = re.sub('-isysroot\s+\S+', '', BASE_CFLAGS)
        if x == BASE_CFLAGS:
            break
        BASE_CFLAGS=x

    arch = distutils.util.get_platform().split('-')[-1]
    if sys.prefix.startswith('/System') and \
            sys.version_info[:2] == (2,5):
        arch = "fat"

    arch_flags = ARCH_BUILD_FLAGS[arch]
    CC=arch_flags['cc']
    CFLAGS = BASE_CFLAGS + ' ' + arch_flags['cflags']
    os.environ['MACOSX_DEPLOYMENT_TARGET'] = arch_flags['target']
    dest = os.path.join(builddir, 'main')
    if not os.path.exists(dest) or (
            os.stat(dest).st_mtime < os.stat(src).st_mtime):
        os.system('"%(CC)s" -o "%(dest)s" "%(src)s" %(CFLAGS)s' % locals())

    dest = os.path.join(builddir, 'main')
    return dest


if __name__ == '__main__':
    main()
