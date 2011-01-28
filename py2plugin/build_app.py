import imp
import sys
import os
import plistlib
import shlex
import shutil
from io import StringIO
import sysconfig
from itertools import chain

from setuptools import Command
from distutils.util import convert_path
from distutils.dir_util import mkpath
from distutils.file_util import copy_file
from distutils import log
from distutils.errors import DistutilsOptionError

from modulegraph.find_modules import find_modules, parse_mf_results
from modulegraph.modulegraph import SourceModule, Package, os_listdir
from modulegraph.util import imp_find_module

import macholib.dyld
import macholib.MachOStandalone
from macholib.util import has_filename_filter

from py2plugin.create_pluginbundle import create_pluginbundle
from py2plugin.util import (fancy_split, byte_compile, make_loader, copy_tree,
    strip_files, in_system_path, makedirs, iter_platform_files, skipscm, copy_file_data,
    os_path_isdir, copy_resource, SCMDIRS)
from py2plugin.filters import not_stdlib_filter
from py2plugin import recipes

from distutils.sysconfig import get_config_var
PYTHONFRAMEWORK=get_config_var('PYTHONFRAMEWORK')

class PythonStandalone(macholib.MachOStandalone.MachOStandalone):
    def copy_dylib(self, src):
        dest = os.path.join(self.dest, os.path.basename(src))
        return copy_dylib(src, dest)

    def copy_framework(self, info):
        destfn = copy_framework(info, self.dest)
        dest = os.path.join(self.dest, info['shortname'] + '.framework')
        self.pending.append((destfn, iter_platform_files(dest)))
        return destfn

def iterRecipes(module=recipes):
    for name in dir(module):
        if name.startswith('_'):
            continue
        check = getattr(getattr(module, name), 'check', None)
        if check is not None:
            yield (name, check)

class Target:
    def __init__(self, script):
        self.script = script
    
    def get_dest_base(self):
        return os.path.basename(os.path.splitext(self.script)[0])
    

def normalize_data_file(fn):
    if isinstance(fn, str):
        fn = convert_path(fn)
        return ('', [fn])
    return fn

def is_system(executable=None):
    if executable is None:
        executable = sys.executable
    return in_system_path(executable)

def installation_info(executable=None, version=None):
    if version is None:
        version = sys.version
    if is_system(executable):
        return version[:3] + " (FORCED: Using vendor Python)"
    else:
        return version[:3]

def force_symlink(src, dst):
    try:
        os.remove(dst)
    except OSError:
        pass
    os.symlink(src, dst)

def create_loader(item, temp_dir, verbose, dry_run):
    # Hm, how to avoid needless recreation of this file?
    slashname = item.identifier.replace('.', os.sep)
    pathname = os.path.join(temp_dir, "%s.py" % slashname)
    if os.path.exists(pathname):
        if verbose:
            print(("skipping python loader for extension %r"
                % (item.identifier,)))
    else:
        mkpath(os.path.dirname(pathname))
        # and what about dry_run?
        if verbose:
            print(("creating python loader for extension %r"
                % (item.identifier,)))

        fname = slashname + os.path.splitext(item.filename)[1]
        source = make_loader(fname)
        if not dry_run:
            open(pathname, "w").write(source)
        else:
            return
    return SourceModule(item.identifier, pathname)

def copy_python_framework(info, dst):
    # XXX - In this particular case we know exactly what we can
    #       get away with.. should this be extended to the general
    #       case?  Per-framework recipes?
    indir = os.path.dirname(os.path.join(info['location'], info['name']))
    outdir = os.path.dirname(os.path.join(dst, info['name']))
    mkpath(os.path.join(outdir, 'Resources'))
    # Since python 3.2, the naming scheme for config files location has considerably
    # complexified. The old, simple way doesn't work anymore. Fortunately, a new module was
    # added to get such paths easily.
    pyconfig_path = sysconfig.get_config_h_filename()
    makefile_path = sysconfig.get_makefile_filename()
    assert pyconfig_path.startswith(indir)
    assert makefile_path.startswith(indir)
    pyconfig_path = pyconfig_path[len(indir)+1:]
    makefile_path = makefile_path[len(indir)+1:]

    # distutils looks for some files relative to sys.executable, which
    # means they have to be in the framework...
    mkpath(os.path.join(outdir, os.path.dirname(pyconfig_path)))
    mkpath(os.path.join(outdir, os.path.dirname(makefile_path)))
    fmwkfiles = [
        os.path.basename(info['name']),
        'Resources/Info.plist',
        pyconfig_path,
        makefile_path,
    ]
    for fn in fmwkfiles:
        copy_file(os.path.join(indir, fn), os.path.join(outdir, fn))

def copy_versioned_framework(info, dst):
    # XXX - Boy is this ugly, but it makes sense because the developer
    #       could have both Python 2.3 and 2.4, or Tk 8.4 and 8.5, etc.
    #       Saves a good deal of space, and I'm pretty sure this ugly
    #       hack is correct in the general case.
    def framework_copy_condition(src):
        # Skip Headers, .svn, and CVS dirs
        return skipscm(src) and os.path.basename(src) != 'Headers'
    
    short = info['shortname'] + '.framework'
    infile = os.path.join(info['location'], short)
    outfile = os.path.join(dst, short)
    version = info['version']
    if version is None:
        condition = framework_copy_condition
    else:
        vsplit = os.path.join(infile, 'Versions').split(os.sep)
        def condition(src, vsplit=vsplit, version=version):
            srcsplit = src.split(os.sep)
            if (
                    len(srcsplit) > len(vsplit) and
                    srcsplit[:len(vsplit)] == vsplit and
                    srcsplit[len(vsplit)] != version and
                    not os.path.islink(src)
                ):
                return False
            # Skip Headers, .svn, and CVS dirs
            return framework_copy_condition(src)
    
    return copy_tree(infile, outfile, preserve_symlinks=True, condition=condition)

def copy_framework(info, dst):
    if info['shortname'] == PYTHONFRAMEWORK:
        copy_python_framework(info, dst)
    else:
        copy_versioned_framework(info, dst)
    return os.path.join(dst, info['name'])

def copy_dylib(src, dst):
    # will be copied from the framework?
    if src != sys.executable:
        copy_file(src, dst)
    return dst

def copy_package_data(package, target_dir):
    """
    Copy any package data in a python package into the target_dir.

    This is a bit of a hack, it would be better to identify python eggs
    and copy those in whole.
    """
    exts = [ i[0] for i in imp.get_suffixes() ]
    exts.append('.py')
    exts.append('.pyc')
    exts.append('.pyo')
    def datafilter(item):
        for e in exts:
            if item.endswith(e):
                return False
        return True

    target_dir = os.path.join(target_dir, *(package.identifier.split('.')))
    for dname in package.packagepath:
        filenames = list(filter(datafilter, os_listdir(dname)))
        for fname in filenames:
            if fname in SCMDIRS:
                # Scrub revision manager junk
                continue
            if fname in ('__pycache__',):
                # Ignore PEP 3147 bytecode cache
                continue
            pth = os.path.join(dname, fname)

            # Check if we have found a package, exclude those
            if os_path_isdir(pth):
                for p in os_listdir(pth):
                    if p.startswith('__init__.') and p[8:] in exts:
                        break

                else:
                    copy_tree(pth, os.path.join(target_dir, fname))
                continue
            else:
                copy_file(pth, os.path.join(target_dir, fname))

def strip_dsym(platfiles, appdir):
    """ Remove .dSYM directories in the bundled application """

    #
    # .dSYM directories are contain detached debugging information and
    # should be completely removed when the "strip" option is specified.
    #
    for dirpath, dnames, fnames in os.walk(appdir):
        for nm in list(dnames):
            if nm.endswith('.dSYM'):
                print("removing debug info: %s/%s"%(dirpath, nm))
                shutil.rmtree(os.path.join(dirpath, nm))
                dnames.remove(nm)
    return [file for file in platfiles if '.dSYM' not in file]

def strip_files_and_report(files, verbose):
    unstripped = 0
    stripfiles = []
    for fn in files:
        unstripped += os.stat(fn).st_size
        stripfiles.append(fn)
        log.info('stripping %s', os.path.basename(fn))
    strip_files(stripfiles, verbose=verbose)
    stripped = 0
    for fn in stripfiles:
        stripped += os.stat(fn).st_size
    log.info('stripping saved %d bytes (%d / %d)',
        unstripped - stripped, stripped, unstripped)

def get_bootstrap(bootstrap):
    if isinstance(bootstrap, str):
        if not os.path.exists(bootstrap):
            bootstrap = imp_find_module(bootstrap)[1]
    return bootstrap

def get_bootstrap_data(bootstrap):
    bootstrap = get_bootstrap(bootstrap)
    if not isinstance(bootstrap, str):
        return bootstrap.getvalue()
    else:
        return open(bootstrap, 'rU').read()

def create_bundle(target, script, dist_dir, plist, runtime_preferences=None):
    base = target.get_dest_base()
    appdir = os.path.join(dist_dir, os.path.dirname(base))
    appname = plist['CFBundleName']
    print("*** creating plugin bundle: %s ***" % (appname,))
    if runtime_preferences:
        plist.setdefault('PyRuntimeLocations', runtime_preferences)
    appdir, plist = create_pluginbundle(appdir, appname, plist=plist)
    resdir = os.path.join(appdir, 'Contents', 'Resources')
    return appdir, resdir, plist

def iter_frameworks(frameworks):
    for fn in frameworks:
        fmwk = macholib.dyld.framework_info(fn)
        if fmwk is None:
            yield fn
        else:
            basename = fmwk['shortname'] + '.framework'
            yield os.path.join(fmwk['location'], basename)

def collect_packagedirs(packages):
    return list(filter(os.path.exists, [
        os.path.join(os.path.realpath(get_bootstrap(pkg)), '')
        for pkg in packages
    ]))

def collect_scripts(targets):
    # these contains file names
    scripts = set()

    for target in targets:
        scripts.add(target.script)
        scripts.update([
            k for k in target.prescripts if isinstance(k, str)
        ])

    return scripts

def collect_filters(filters):
    return [has_filename_filter] + list(filters)

def finalize_modulefinder(mf, temp_dir):
    for item in mf.flatten():
        if isinstance(item, Package) and item.filename == '-':
            fn = os.path.join(temp_dir, 'empty_package', '__init__.py')
            if not os.path.exists(fn):
                dn = os.path.dirname(fn)
                if not os.path.exists(dn):
                    os.makedirs(dn)
                fp = open(fn, 'w')
                fp.close()

            item.filename = fn

    py_files, extensions = parse_mf_results(mf)
    py_files = list(py_files)
    extensions = list(extensions)
    return py_files, extensions

def filter_dependencies(mf, filters):
    print("*** filtering dependencies ***")
    nodes_seen, nodes_removed, nodes_orphaned = mf.filterStack(filters)
    print('%d total' % (nodes_seen,))
    print('%d filtered' % (nodes_removed,))
    print('%d orphaned' % (nodes_orphaned,))
    print('%d remaining' % (nodes_seen - nodes_removed,))

class py2plugin(Command):
    description = "create a Mac OS X application or plugin from Python scripts"
    # List of option tuples: long name, short name (None if no short
    # name), and help string.

    user_options = [
        ("plugin=", None,
         "puglin bundle to be built"),
        ('optimize=', 'O',
         "optimization level: -O1 for \"python -O\", "
         "-O2 for \"python -OO\", and -O0 to disable [default: -O0]"),
        ("includes=", 'i',
         "comma-separated list of modules to include"),
        ("packages=", 'p',
         "comma-separated list of packages to include"),
        ("iconfile=", None,
         "Icon file to use"),
        ("excludes=", 'e',
         "comma-separated list of modules to exclude"),
        ("dylib-excludes=", 'E',
         "comma-separated list of frameworks or dylibs to exclude"),
        ("resources=", 'r',
         "comma-separated list of additional data files and folders to include (not for code!)"),
        ("frameworks=", 'f',
         "comma-separated list of additional frameworks and dylibs to include"),
        ("plist=", 'P',
         "Info.plist template file, dict, or plistlib.Plist"),
        ("no-strip", None,
         "do not strip debug and local symbols from output"),
        ("semi-standalone", 's',
         "depend on an existing installation of Python " + installation_info()),
        ("alias", 'A',
         "Use an alias to current source file (for development only!)"),
        ("argv-inject=", None,
         "Inject some commands into the argv"),
        ("use-pythonpath", None,
         "Allow PYTHONPATH to effect the interpreter's environment"),
        ('bdist-base=', 'b',
         'base directory for build library (default is build)'),
        ('dist-dir=', 'd',
         "directory to put final built distributions in (default is dist)"),
        ('site-packages', None,
         "include the system and user site-packages into sys.path"),
        ('debug-modulegraph', None,
         'Drop to pdb console after the module finding phase is complete'),
        ("debug-skip-macholib", None,
         "skip macholib phase (app will not be standalone!)"),
        ]

    boolean_options = [
        "no-strip",
        "site-packages",
        "semi-standalone",
        "alias",
        "use-pythonpath",
        "debug-modulegraph",
        "debug-skip-macholib",
    ]

    def initialize_options(self):
        self.app = None
        self.plugin = None
        self.bdist_base = None
        self.optimize = 0
        self.no_strip = False
        self.iconfile = None
        self.alias = 0
        self.argv_inject = None
        self.site_packages = False
        self.use_pythonpath = False
        self.includes = None
        self.packages = None
        self.excludes = None
        self.dylib_excludes = None
        self.frameworks = None
        self.resources = None
        self.plist = None
        self.semi_standalone = is_system()
        self.dist_dir = None
        self.debug_skip_macholib = False
        self.debug_modulegraph = False
        self.filters = []
    
    def finalize_options(self):
        self.optimize = int(self.optimize)
        if self.argv_inject and isinstance(self.argv_inject, str):
            self.argv_inject = shlex.split(self.argv_inject)
        self.includes = set(fancy_split(self.includes))
        self.includes.add('encodings.*')
        self.packages = set(fancy_split(self.packages))
        self.excludes = set(fancy_split(self.excludes))
        self.excludes.add('readline')
        # included by apptemplate
        self.excludes.add('site')
        dylib_excludes = fancy_split(self.dylib_excludes)
        self.dylib_excludes = []
        for fn in dylib_excludes:
            try:
                res = macholib.dyld.framework_find(fn)
            except ValueError:
                try:
                    res = macholib.dyld.dyld_find(fn)
                except ValueError:
                    res = fn
            self.dylib_excludes.append(res)
        self.resources = fancy_split(self.resources)
        frameworks = fancy_split(self.frameworks)
        self.frameworks = []
        for fn in frameworks:
            try:
                res = macholib.dyld.framework_find(fn)
            except ValueError:
                res = macholib.dyld.dyld_find(fn)
            while res in self.dylib_excludes:
                self.dylib_excludes.remove(res)
            self.frameworks.append(res)
        if not self.plist:
            self.plist = {}
        if isinstance(self.plist, str):
            self.plist = plistlib.Plist.fromFile(self.plist)
        if isinstance(self.plist, plistlib.Dict):
            self.plist = dict(self.plist.__dict__)
        else:
            self.plist = dict(self.plist)

        self.set_undefined_options('bdist',
                                   ('dist_dir', 'dist_dir'),
                                   ('bdist_base', 'bdist_base'))

        if self.semi_standalone:
            self.filters.append(not_stdlib_filter)

        if self.iconfile is None and 'CFBundleIconFile' not in self.plist:
            # Default is the generic applet icon in the framework
            iconfile = os.path.join(sys.prefix, 'Resources', 'Python.app',
                'Contents', 'Resources', 'PythonApplet.icns')
            if os.path.exists(iconfile):
                self.iconfile = iconfile

        self.runtime_preferences = list(self.get_runtime_preferences())


    def get_default_plist(self):
        # XXX - this is all single target stuff
        plist = {}
        target = self.targets[0]

        version = self.distribution.get_version()
        plist['CFBundleVersion'] = version

        name = self.distribution.get_name()
        if name == 'UNKNOWN':
            base = target.get_dest_base()
            name = os.path.basename(base)
        plist['CFBundleName'] = name

        return plist

    def get_runtime(self, prefix=None, version=None):
        # XXX - this is a bit of a hack!
        #       ideally we'd use dylib functions to figure this out
        if prefix is None:
            prefix = sys.prefix
        if version is None:
            version = sys.version
        version = version[:3]
        info = None
        if os.path.exists(os.path.join(prefix, ".Python")):
            # We're in a virtualenv environment, locate the real prefix
            fn = os.path.join(prefix, "lib", "python%d.%d"%(sys.version_info[:2]), "orig-prefix.txt")
            if os.path.exists(fn):
                prefix = open(fn, 'rU').read().strip()

        try:
            fmwk = macholib.dyld.framework_find(prefix)
        except ValueError:
            info = None
        else:
            info = macholib.dyld.framework_info(fmwk)

        if info is not None:
            dylib = info['name']
            runtime = os.path.join(info['location'], info['name'])
        else:
            dylib = 'libpython%s.dylib' % (sys.version[:3],)
            runtime = os.path.join(prefix, 'lib', dylib)
        return dylib, runtime
    
    def get_runtime_preferences(self, prefix=None, version=None):
        dylib, runtime = self.get_runtime(prefix=prefix, version=version)
        yield os.path.join('@executable_path', '..', 'Frameworks', dylib)
        if self.semi_standalone or self.alias:
            yield runtime

    def run(self):
        build = self.reinitialize_command('build')
        build.build_base = self.bdist_base
        build.run()
        self.create_directories()
        self.fixup_distribution()
        self.initialize_plist()

        sys_old_path = sys.path[:]
        extra_paths = [
            os.path.dirname(target.script)
            for target in self.targets
        ]
        extra_paths.extend([build.build_platlib, build.build_lib])
        self.additional_paths = [
            os.path.abspath(p)
            for p in extra_paths
            if p is not None
        ]
        sys.path[:0] = self.additional_paths

        # this needs additional_paths
        self.initialize_prescripts()

        try:
            if self.alias:
                self.run_alias()
            else:
                self.run_normal()
        finally:
            sys.path = sys_old_path


    def iter_data_files(self):
        dist = self.distribution
        allres = chain(getattr(dist, 'data_files', ()) or (), self.resources)
        for (path, files) in map(normalize_data_file, allres):
            for fn in files:
                yield fn, os.path.join(path, os.path.basename(fn))
    
    def get_plist_options(self):
        return dict(
            PyOptions=dict(
                use_pythonpath=bool(self.use_pythonpath),
                site_packages=bool(self.site_packages),
                alias=bool(self.alias),
                optimize=self.optimize,
            ),
        )

    
    def initialize_plist(self):
        plist = self.get_default_plist()
        for target in self.targets:
            plist.update(getattr(target, 'plist', {}))
        plist.update(self.plist)
        plist.update(self.get_plist_options())

        if self.iconfile:
            iconfile = self.iconfile
            if not os.path.exists(iconfile):
                iconfile = iconfile + '.icns'
            if not os.path.exists(iconfile):
                raise DistutilsOptionError("icon file must exist: %r"
                    % (self.iconfile,))
            self.resources.append(iconfile)
            plist['CFBundleIconFile'] = os.path.basename(iconfile)
        self.plist = plist
        return plist

    def run_alias(self):
        self.app_files = []
        for target in self.targets:
            dst = self.build_alias_executable(target, target.script)
            self.app_files.append(dst)
    
    def process_recipes(self, mf, filters, flatpackages, loader_files):
        rdict = dict(iterRecipes())
        while True:
            for name, check in rdict.items():
                rval = check(self, mf)
                if rval is None:
                    continue
                # we can pull this off so long as we stop the iter
                del rdict[name]
                print('*** using recipe: %s ***' % (name,))
                self.packages.update(rval.get('packages', ()))
                for pkg in rval.get('flatpackages', ()):
                    if isinstance(pkg, str):
                        pkg = (os.path.basename(pkg), pkg)
                    flatpackages[pkg[0]] = pkg[1]
                filters.extend(rval.get('filters', ()))
                loader_files.extend(rval.get('loader_files', ()))
                newbootstraps = list(map(get_bootstrap, rval.get('prescripts', ())))

                for fn in newbootstraps:
                    if isinstance(fn, str):
                        mf.run_script(fn)
                for target in self.targets:
                    target.prescripts.extend(newbootstraps)
                break
            else:
                break
    
    def run_normal(self):
        debug = 4 if self.debug_modulegraph else 0
        mf = find_modules(scripts=collect_scripts(self.targets), includes=self.includes,
            packages=self.packages, excludes=self.excludes, debug=debug)
        filters = collect_filters(self.filters)
        flatpackages = {}
        loader_files = []
        self.process_recipes(mf, filters, flatpackages, loader_files)

        if self.debug_modulegraph:
            import pdb
            pdb.Pdb().set_trace()

        filter_dependencies(mf, filters)

        py_files, extensions = finalize_modulefinder(mf, self.temp_dir)
        pkgdirs = collect_packagedirs(self.packages)
        self.create_binaries(py_files, pkgdirs, extensions, loader_files)
    
    def create_directories(self):
        bdist_base = self.bdist_base
        if self.semi_standalone:
            self.bdist_dir = os.path.join(bdist_base,
                'python%s-semi_standalone' % (sys.version[:3],), 'app')
        else:
            self.bdist_dir = os.path.join(bdist_base,
                'python%s-standalone' % (sys.version[:3],), 'app')

        self.collect_dir = os.path.abspath(
            os.path.join(self.bdist_dir, "collect"))
        self.mkpath(self.collect_dir)

        self.temp_dir = os.path.abspath(os.path.join(self.bdist_dir, "temp"))
        self.mkpath(self.temp_dir)

        self.dist_dir = os.path.abspath(self.dist_dir)
        self.mkpath(self.dist_dir)

        self.ext_dir = os.path.join(self.bdist_dir, 'lib-dynload')
        self.mkpath(self.ext_dir)

        self.framework_dir = os.path.join(self.bdist_dir, 'Frameworks')
        self.mkpath(self.framework_dir)

    def create_binaries(self, py_files, pkgdirs, extensions, loader_files):
        print("*** create binaries ***")
        pkgexts = []
        copyexts = []
        extmap = {}
        def packagefilter(mod, pkgdirs=pkgdirs):
            fn = os.path.realpath(getattr(mod, 'filename', None))
            if fn is None:
                return None
            for pkgdir in pkgdirs:
                if fn.startswith(pkgdir):
                    return None
            return fn
        if pkgdirs:
            py_files = list(filter(packagefilter, py_files))
        for ext in extensions:
            fn = packagefilter(ext)
            if fn is None:
                fn = os.path.realpath(getattr(ext, 'filename', None))
                pkgexts.append(ext)
            else:
                if '.' in ext.identifier:
                    py_files.append(create_loader(ext, self.temp_dir, self.verbose, self.dry_run))
                copyexts.append(ext)
            extmap[fn] = ext

        # byte compile the python modules into the target directory
        print("*** byte compile python files ***")
        byte_compile(py_files,
                     target_dir=self.collect_dir,
                     optimize=self.optimize,
                     force=True,
                     verbose=self.verbose,
                     dry_run=self.dry_run)

        for item in py_files:
            if not isinstance(item, Package): continue
            copy_package_data(item, self.collect_dir)

        self.lib_files = []
        self.app_files = []

        for path, files in loader_files:
            dest = os.path.join(self.collect_dir, path)
            self.mkpath(dest)
            for fn in files:
                destfn = os.path.join(dest, os.path.basename(fn))
                if os.path.isdir(fn):
                    copy_tree(fn, destfn, preserve_symlinks=False)
                else:
                    self.copy_file(fn, destfn)

        # build the executables
        for target in self.targets:
            dst = self.build_executable(target, pkgexts, copyexts, target.script)
            exp = os.path.join(dst, 'Contents', 'MacOS')
            execdst = os.path.join(exp, 'python')
            if self.semi_standalone:
                force_symlink(sys.executable, execdst)
            else:
                if os.path.exists(os.path.join(sys.prefix, ".Python")):
                    fn = os.path.join(sys.prefix, "lib", "python%d.%d"%(sys.version_info[:2]), "orig-prefix.txt")
                    if os.path.exists(fn):
                        prefix = open(fn, 'rU').read().strip()

                    rest_path = sys.executable[len(sys.prefix)+1:]
                    if rest_path.startswith('.'):
                        rest_path = rest_path[1:]

                    print("XXXX", os.path.join(prefix, rest_path))
                    self.copy_file(os.path.join(prefix, rest_path), execdst)

                else:
                    self.copy_file(sys.executable, execdst)
            if not self.debug_skip_macholib:
                mm = PythonStandalone(dst, executable_path=exp)
                dylib, runtime = self.get_runtime()
                if self.semi_standalone:
                    mm.excludes.append(runtime)
                else:
                    mm.mm.run_file(runtime)
                for exclude in self.dylib_excludes:
                    info = macholib.dyld.framework_info(exclude)
                    if info is not None:
                        exclude = os.path.join(
                            info['location'], info['shortname'] + '.framework')
                    mm.excludes.append(exclude)
                for fmwk in self.frameworks:
                    mm.mm.run_file(fmwk)
                platfiles = mm.run()
                if not self.no_strip and not self.dry_run:
                    platfiles = strip_dsym(platfiles, self.appdir)
                    strip_files_and_report(platfiles, self.verbose)
            self.app_files.append(dst)
    
    def fixup_distribution(self):
        dist = self.distribution

        # Trying to obtain plugin from dist for backward compatibility
        # reasons.
        plugin = dist.plugin
        # If we can get suitable value from self.plugin, we prefer it.
        if self.plugin is not None:
            plugin = self.plugin

        # Convert our args into target objects.
        self.targets = [Target(script) for script in plugin]
        if len(self.targets) != 1:
            # XXX - support multiple targets?
            raise DistutilsOptionError("Multiple targets not currently supported")

        # make sure all targets use the same directory, this is
        # also the directory where the pythonXX.dylib must reside
        paths = set()
        for target in self.targets:
            paths.add(os.path.dirname(target.get_dest_base()))

        if len(paths) > 1:
            raise DistutilsOptionError(
                  "all targets must use the same directory: %s" %
                  ([p for p in paths],))
        if paths:
            app_dir = paths.pop() # the only element
            if os.path.isabs(app_dir):
                raise DistutilsOptionError(
                      "app directory must be relative: %s" % (app_dir,))
            self.app_dir = os.path.join(self.dist_dir, app_dir)
            self.mkpath(self.app_dir)
        else:
            # Do we allow to specify no targets?
            # We can at least build a zipfile...
            self.app_dir = self.bdist_dir

    def initialize_prescripts(self):
        prescripts = []
        if self.site_packages or self.alias:
            prescripts.append('site_packages')

        if self.argv_inject is not None:
            prescripts.append('argv_inject')
            prescripts.append(
                StringIO('_argv_inject(%r)\n' % (self.argv_inject,)))

        if not self.alias:
            prescripts.append('disable_linecache')
            prescripts.append('boot_plugin')
        else:
            if self.additional_paths:
                prescripts.append('path_inject')
                prescripts.append(
                    StringIO('_path_inject(%r)\n' % (self.additional_paths,)))
            prescripts.append('boot_aliasplugin')
        newprescripts = []
        for s in prescripts:
            if isinstance(s, str):
                newprescripts.append(get_bootstrap('py2plugin.bootstrap.' + s))
            else:
                newprescripts.append(s)

        for target in self.targets:
            prescripts = getattr(target, 'prescripts', [])
            target.prescripts = newprescripts + prescripts
    
    def build_alias_executable(self, target, script):
        # Build an alias executable for the target
        appdir, resdir, plist = create_bundle(target, script, self.dist_dir, self.plist, self.runtime_preferences)

        # symlink python executable
        execdst = os.path.join(appdir, 'Contents', 'MacOS', 'python')
        prefixPathExecutable = os.path.join(sys.prefix, 'bin', 'python')
        if os.path.exists(prefixPathExecutable):
            pyExecutable = prefixPathExecutable
        else:
            pyExecutable = sys.executable
        force_symlink(pyExecutable, execdst)

        # make PYTHONHOME
        pyhome = os.path.join(resdir, 'lib', 'python' + sys.version[:3])
        realhome = os.path.join(sys.prefix, 'lib', 'python' + sys.version[:3])
        makedirs(pyhome)
        force_symlink('../../site.py', os.path.join(pyhome, 'site.py'))
        force_symlink(
            os.path.join(realhome, 'config'),
            os.path.join(pyhome, 'config'))
            
        
        # symlink data files
        # XXX: fixme: need to integrate automatic data conversion
        for src, dest in self.iter_data_files():
            dest = os.path.join(resdir, dest)
            if src == dest:
                continue
            makedirs(os.path.dirname(dest))
            force_symlink(os.path.abspath(src), dest)

        # symlink frameworks
        for src in iter_frameworks(self.frameworks):
            dest = os.path.join(
                appdir, 'Contents', 'Frameworks', os.path.basename(src))
            if src == dest:
                continue
            makedirs(os.path.dirname(dest))
            force_symlink(os.path.abspath(src), dest)

        bootfn = '__boot__'
        bootfile = open(os.path.join(resdir, bootfn + '.py'), 'w')
        for fn in target.prescripts:
            bootfile.write(get_bootstrap_data(fn))
            bootfile.write('\n\n')
        bootfile.write('try:\n')
        bootfile.write('    _run(%r)\n' % os.path.realpath(script))
        bootfile.write('except KeyboardInterrupt:\n')
        bootfile.write('    pass\n')
        bootfile.close()

        target.appdir = appdir
        return appdir

    def build_executable(self, target, pkgexts, copyexts, script):
        # Build an executable for the target
        appdir, resdir, plist = create_bundle(target, script, self.dist_dir, self.plist, self.runtime_preferences)
        self.appdir = appdir
        self.resdir = resdir
        self.plist = plist

        for src, dest in self.iter_data_files():
            dest = os.path.join(resdir, dest)
            self.mkpath(os.path.dirname(dest))
            copy_resource(src, dest, dry_run=self.dry_run)

        bootfn = '__boot__'
        bootfile = open(os.path.join(resdir, bootfn + '.py'), 'w')
        for fn in target.prescripts:
            bootfile.write(get_bootstrap_data(fn))
            bootfile.write('\n\n')
        bootfile.write('_run(%r)\n' % (os.path.basename(script),))
        bootfile.close()

        self.copy_file(script, resdir)
        pydir = os.path.join(resdir, 'lib', 'python' + sys.version[:3])
        self.mkpath(pydir)
        force_symlink('../../site.py', os.path.join(pydir, 'site.py'))
        realcfg = os.path.dirname(sysconfig.get_makefile_filename())
        cfgdir = os.path.join(resdir, os.path.relpath(realcfg, sys.prefix))
        real_include = os.path.join(sys.prefix, 'include')
        if self.semi_standalone:
            force_symlink(realcfg, cfgdir)
            force_symlink(real_include, os.path.join(resdir, 'include'))
        else:
            self.mkpath(cfgdir)
            for fn in 'Makefile', 'Setup', 'Setup.local', 'Setup.config':
                rfn = os.path.join(realcfg, fn)
                if os.path.exists(rfn):
                    self.copy_file(rfn, os.path.join(cfgdir, fn))

            # see copy_python_framework() for explanation.
            pyconfig_path = sysconfig.get_config_h_filename()
            pyconfig_path_relative = os.path.relpath(os.path.dirname(pyconfig_path), sys.prefix)
            inc_dir = os.path.join(resdir, pyconfig_path_relative)
            self.mkpath(inc_dir)
            self.copy_file(pyconfig_path, os.path.join(inc_dir, 'pyconfig.h'))


        copy_tree(self.collect_dir, pydir)
        
        ext_dir = os.path.join(pydir, os.path.basename(self.ext_dir))
        copy_tree(self.ext_dir, ext_dir, preserve_symlinks=True)
        copy_tree(self.framework_dir, os.path.join(appdir, 'Contents', 'Frameworks'), 
            preserve_symlinks=True)
        for pkg in self.packages:
            pkg = get_bootstrap(pkg)
            dst = os.path.join(pydir, os.path.basename(pkg))
            self.mkpath(dst)
            copy_tree(pkg, dst)
        for copyext in copyexts:
            fn = os.path.join(ext_dir,
                (copyext.identifier.replace('.', os.sep) +
                os.path.splitext(copyext.filename)[1])
            )
            self.mkpath(os.path.dirname(fn))
            copy_file_data(copyext.filename, fn, dry_run=self.dry_run)

        target.appdir = appdir
        return appdir

