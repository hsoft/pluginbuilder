.. pluginbuilder documentation master file, created by Virgil Dupras
   sphinx-quickstart on Sat Jul 31 09:59:24 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pluginbuilder - Create standalone Mac OS X plugins with Python
==============================================================

pluginbuilder is a Python package which will allow you to make standalone plugins from Python 
scripts.This plugin can then be used by an Objective-C application (through ``NSBundle``). 
pluginbuilder is a fork of `py2app`_, but without the distutils based command or the ability to 
create application bundles.

Why forking py2app just to remove stuff from it? Because the resulting code is much simpler
(distutils sucks), which makes it much easier to maintain. The release of Python 3.2 broke py2app
and being, I think, the only user of its "plugin" feature, I had to fix it myself and was thus
exposed to the messiness of the code. I had to do something about it.

The logical name for such a fork of py2app would have been py2plugin, but a project named "pyplugin"
already exists, hence this name.

Online Resources
----------------

Source code repository:
    http://bitbucket.org/hsoft/pluginbuilder

PyPI Entry:
    http://pypi.python.org/pypi/pluginbuilder/

Issue tracker:
    http://bitbucket.org/hsoft/pluginbuilder/issues

Online Documentation (this doc):
    http://www.hardcoded.net/docs/pluginbuilder

If you're looking for help, pay special attention to the ``examples`` folder in the source, which demonstrates some (one in fact...) common use cases.

License
-------

pluginbuilder may be distributed under the `MIT`_ or `PSF`_ open source
licenses.

Copyright (c) 2004-2006 Bob Ippolito <bob at redivi.com>.

Copyright (c) 2010 Ronald Oussoren <ronaldoussoren at mac.com>.

Copyright (c) 2011 Virgil Dupras <hsoft at hardcoded.net>.

Contents:

.. toctree::
   :maxdepth: 2
   
   whyplugin
   install
   usage
   embed
   examples
   recipes
   implementation

.. _`py2app`: http://bitbucket.org/ronaldoussoren/py2app
.. _`PSF`: http://www.python.org/psf/license.html
.. _`MIT`: http://www.opensource.org/licenses/mit-license.php
