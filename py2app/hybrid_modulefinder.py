import os.path
from modulefinder import ModuleFinder

def wrap_module(m):
    if m is not None:
        m.identifier = m.__name__
        m.filename = m.__file__
        # I'm not too sure what packagepath is... I'm taking a guess here
        if m.__file__ and os.path.basename(m.__file__) == '__init__.py':
            m.packagepath = os.path.dirname(m.__file__)
        else:
            m.packagepath = None
    return m

class HybridModuleFinder(ModuleFinder):
    # A ModuleFinder that implements modulegraph's methods used by py2app
    def filterStack(self, filters):
        removed = 0
        seen = len(self.modules)
        for name, m in list(self.modules.items()):
            m = wrap_module(m)
            for f in filters:
                if not f(m):
                    del self.modules[name]
                    removed += 1
                    break
        return (seen, removed, 0)
    
    def findNode(self, name):
        return wrap_module(self.modules.get(name))
    
    def flatten(self):
        return [wrap_module(m) for m in self.modules.values()]
    
    def include_module(self, includename):
        includename = includename.strip()
        starimport = False
        if includename.endswith('.*'):
            includename = includename[:-2]
            starimport = True
        m = self.import_module(includename, includename, None)
        if m is not None and starimport:
            self.ensure_fromlist(m, '*')
        
