__version__ = '1.0.1'

# If we import build_plugin as top level imports, then it's impossible to get __version__ without
# importing pluginbuilder's dependencies first. So, import build_plugin only when it's called.

def build_plugin(*args, **kwargs):
    from .build_plugin import build_plugin as real_build_plugin
    real_build_plugin(*args, **kwargs)
