Implementation Details
======================

For those interested in the implementation of py2plugin, here's a quick
rundown of what happens. The main function of the building process is
``py2plugin.build_app.build_plugin()``.


Argument Parsing
----------------

Arguments are parsed and put into the ``Options``, which sanitizes them and holds them for future
reference.

Dependency resolution via modulegraph
-------------------------------------

The main script is compiled to Python bytecode and analyzed by modulegraph
for ``import`` bytecode. It uses this to build a dependency graph of all
involved Python modules.

The dependency graph is primed with any ``--includes``, ``--excludes``, or
``--packages`` options.


Apply recipes
-------------

All of the :doc:`recipes` will be run in order to find library-specific tweaks
necessary to build the application properly.


Apply filters
-------------

All filters specified in recipes will be run to filter out the dependency graph.

Create the .plugin bundle
-------------------------

A plugin bundle will be created with the name of your script.

The ``Contents/Info.plist`` will be created from the ``dict`` or filename
given in the ``plist`` option. py2plugin will fill in any missing keys as
necessary.

A ``__boot__.py`` script will be created in the ``Contents/Resources/`` folder of the plugin bundle.
This script runs any prescripts used by the application and then your main script.

If the ``--alias`` option is being used, the build procedure is finished.

The main script of your application will be copied *as-is* to the 
``Contents/Resources/`` folder of the application bundle. If you want to
obfuscate anything (by having it as a ``.pyc`` in the zip), then you
*must not* place it in the main script!

All dependencies, as well as packages that were explicitly included with the ``packages`` option, or
by a recipe, will be placed in ``Contents/Resources/lib/python3.X/``.

Include Mach-O dependencies
---------------------------

`macholib`_ is used to ensure the application will run on other computers
without the need to install additional components. All Mach-O
files (executables, frameworks, bundles, extensions) used by the application
are located and copied into the application bundle.

The Mach-O load commands for these Mach-O files are then rewritten to be
``@executable_path/../Frameworks/`` relative, so that dyld knows to find
them inside the application bundle.

``Python.framework`` is special-cased here so as to only include the bare
minimum, otherwise the documentation, entire standard library, etc. would've
been included.

Strip the result
----------------

Unless the ``--no-strip`` option is specified, all Mach-O files in the 
application bundle are stripped using the ``strip`` tool. This removes
debugging symbols to make your application smaller.


Copy Python configuration
-------------------------

The Python configuration, which is used by ``distutils`` and ``pkg_resources``
is copied to ``Contents/Resources/lib/python3.X/config/``. This is needed
to acquire settings relevant to the way Python was built.

.. _`macholib`: http://pypi.python.org/pypi/macholib/