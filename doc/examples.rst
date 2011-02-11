Examples
========

The ``examples`` subfolder contains a few examples to show the the way to enlightenment. Each
project have their own extra dependencies, but they of course all require ``pluginbuilder`` to be
installed. Each of the example have a ``build.py`` file in them, so all you have to do to build them
is (after you've installed required dependencies) to do::

    $ python build.py

You'll normally end up with a usage .app file in the ``build/release`` subfolder.

Ok, actually there's only one example, and I can't think of another use for pluginbuilder than to 
wrap a PyObjC-enabled app, but let's pretend there's more than one example...

simple_pyobjc
-------------

**Extra dependencies:** `PyObjC <http://pyobjc.sourceforge.net/>`__.

This is a simple gui-enabled application which uses Python for its core logic. It asks for a name
and then displays "Hello {name}!".
