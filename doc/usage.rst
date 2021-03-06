Usage
=====

There are two ways to invoke ``pluginbuilder``: By command line or directly through Python. In both
cases, the same arguments are used. Here's an example command line invocation::

    $ pluginbuilder myscript.py --excludes somepkg someotherpkg --alias --verbose

And an example of invocation through Python::

    >>> from pluginbuilder import build_plugin
    >>> build_plugin('myscript.py', excludes=['somepkg', 'someotherpkg'], alias=True, verbose=True)

When you invoke ``pluginbuilder``, it does its thing and then puts the resulting ``myscript.plugin`` 
in the "dist" folder (You can change the destination folder with the ``dist_dir`` argument)

Argument Formatting
-------------------

Although the argument used by command line and direct invocation are the same, they're formatted
differently. The boolean flags are turned on with ``--argname`` if their default value is off, and
turned off with ``--no-argname`` if their default value is on. Arguments receiving a value (anything
not boolean) are given in the ``--argname value`` format. If the argument receives a list, it must 
be given in the ``--argname item1 item2`` format. If the argument value contains a space character,
then the value should be "quoted" (Example: ``--argname item1 "item 2"``. Arguments having
underscores ("_") in their name have them replaced by dashes ("-") for command line invocation.

Argument List
-------------

main_script_path (string):
    The path to the script you want to transform into a plugin.

includes (list):
    A list of modules to include. Normally, the automatic dependency detection system does a good
    job of automatically detecting that stuff, but we never know.

packages (list):
    A list of packages to include.

excludes (list):
    A list of packages to excludes. This is needed when, for example, one of your module makes a
    conditional import which you don't need in the final product, but which is picked up by the
    automatic dependencies detection anyway.

dylib-excludes (list):
    A list of frameworks or dylibs to exclude.

resources (list):
    A list of resources to include in your plugin.

frameworks (list):
    A list of frameworks or dylibs to include.

plist (string):
    The path to a Info.plist template to use instead of the default one.

argv_inject (string):
    Inject some commands into the argv.

bdist_base (string default='build'):
    The folder which will be used by ``pluginbuilder`` to build the plugin (in short, a temp dir).

dist_dir (string default='dist'):
    The folder in which the finished plugin will be put.

alias (bool default=False):
    Instead of copying stuff in the plugin, make symlinks instead. This way, you can modify your
    Python code and run it through the plugin without having to re-build the plugin.

strip (bool default=True):
    Strip debug and local symbols from output.

use_pythonpath (bool default=False):
    Allow PYTHONPATH to effect the interpreter's environment.

site_packages (bool default=False):
    Include the whole system's site-package in the plugin.

debug_modulegraph (bool default=False):
    Drop to pdb console after the module finding phase is complete.

debug_skip_macholib (bool default=False):
    skip macholib phase (app will not be standalone!).

Additional functions
--------------------

There are additional functions exposed in pluginbuilder to help you do plugin-less embedding.
If, for example, you're using the Python API directly in your Objective-C code and would rather
embed Python directly in your main app instead of a plugin, you can use helper functions in
pluginbuilder to help you do that. First, there's ``get_python_header_folder()``, which simply
returns the path to your current python's header folder. You can use this in your build script to
create a symbolic link to it in your project's build folder which you can then add to your XCode
project's search path. Then there's ``copy_embeddable_python_dylib(dst)`` which copies the dylib
of your python framework's installation to ``dst`` and automatically changes its install path
to ``@rpath/Python`` so that you can embed it and link to it in your XCode project. Finally, there's
``collect_dependencies(main_script_path, dst, **options)`` which does the same dependency collection
process as it does when it builds a plugin, but without the rest of the hocus pocus. It puts it
directly in ``dst``. The options that it takes are the same as in ``build_plugin()``.
