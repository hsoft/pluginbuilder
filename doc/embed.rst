How to embed your plugin in your application
============================================

Once you've built your plugin, you need to load it in your Objective-C app. A while ago, I `explained how to do it <http://www.hardcoded.net/articles/embedded-pyobjc.htm>`__ with ``py2app``, but it's still relevant to pluginbuilder.

Let's say that we want to build a PyObjC application embedding Python that simply displays a list of strings in a ``NSTableView``. Let's first write our Python class::

    class Foobar:
        def __init__(self):
            self.strings = ['foo', 'bar', 'baz']
        
        def count(self):
            return len(self.strings)
        
        def string_at_index(self, index):
            return self.strings[index]

This is, of course, stupidly-engineered for the purpose of the example. The next thing we have to do is to create an interface that converts calls with Objective-C conventions to calls with Python conventions::

    import objc
    from Foundation import NSObject
    from foobar import Foobar
    
    class PyFoobar(NSObject):
        def init(self):
            self = super(PyFoobar, self).init()
            self.py = Foobar()
            return self
        
        @objc.signature('i@:')
        def count(self):
            return self.py.count()
        
        @objc.signature('@@:i')
        def stringAtIndex_(self, index):
            return self.py.string_at_index(index)

The signature decorators are required so that PyObjC correctly converts ``int``s. Methods that have nothing but ``NSObject`` subclasses as arguments or return values don't need any signature. 

Now that we have this, we're ready to :doc:`build a plugin with pluginbuilder <usage>`. Use the interface python script as the "main plugin script". Once you have the plugin, you can now create your Objective-C project. The first thing you should do is to create a header file describing the interface of your Python classes:

.. code-block:: objective-c
    
    @interface PyFoobar : NSObject {}
    - (int)count;
    - (NSString *)stringAtIndex:(int)aIndex;
    @end

Now comes the "magic" part where you instantiate your python classes in Objective-C. This is done through ``NSBundle``. Let's imagine that we have a NIB-based ``NSWindowController`` with a table view that has itself as its datasource and a ``PyFoobar *py`` member. Its implementation would look like that:

.. code-block:: objective-c

    - (void)awakeFromNib
    {
        NSString *pluginPath = [[NSBundle mainBundle] pathForResource:@"your_plugin"
            ofType:@"plugin"];
        NSBundle *pluginBundle = [NSBundle bundleWithPath:pluginPath];
        Class pyClass = [pluginBundle classNamed:@"PyFoobar"];
        py = [[pyClass alloc] init];
    }
    
    - (void)dealloc
    {
        [py release];
        [super dealloc];
    }
    
    - (NSInteger)numberOfRowsInTableView:(NSTableView *)tableView
    {
        return [py count];
    }

    - (id)tableView:(NSTableView *)tableView objectValueForTableColumn:(NSTableColumn *)column
        row:(NSInteger)row
    {
        return [py stringAtRow:row];
    }

You now have a working Objective-C application that embeds Python code!