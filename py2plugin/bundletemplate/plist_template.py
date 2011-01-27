import sys
import py2plugin
__all__ = ['infoPlistDict']

def infoPlistDict(CFBundleExecutable, plist={}):
    CFBundleExecutable = unicode(CFBundleExecutable)
    NSPrincipalClass = u''.join(CFBundleExecutable.split())
    version = sys.version[:3]
    pdict = dict(
        CFBundleDevelopmentRegion=u'English',
        CFBundleDisplayName=plist.get('CFBundleName', CFBundleExecutable),
        CFBundleExecutable=CFBundleExecutable,
        CFBundleIconFile=CFBundleExecutable,
        CFBundleIdentifier=u'org.pythonmac.unspecified.%s' % (NSPrincipalClass,),
        CFBundleInfoDictionaryVersion=u'6.0',
        CFBundleName=CFBundleExecutable,
        CFBundlePackageType=u'BNDL',
        CFBundleShortVersionString=plist.get('CFBundleVersion', u'0.0'),
        CFBundleSignature=u'????',
        CFBundleVersion=u'0.0',
        LSHasLocalizedDisplayName=False,
        NSAppleScriptEnabled=False,
        NSHumanReadableCopyright=u'Copyright not specified',
        NSMainNibFile=u'MainMenu',
        NSPrincipalClass=NSPrincipalClass,
        PyMainFileNames=[u'__boot__'],
        PyResourcePackages=[ (s % version) for s in [
            u'lib/python%s',
            u'lib/python%s/lib-dynload',
            u'lib/python%s/site-packages.zip',
        ]] + [ u'lib/python%s.zip' % version.replace('.', '') ],
        PyRuntimeLocations=[(s % version) for s in [
            u'@executable_path/../Frameworks/Python.framework/Versions/%s/Python',
            u'~/Library/Frameworks/Python.framework/Versions/%s/Python',
            u'/Library/Frameworks/Python.framework/Versions/%s/Python',
            u'/Network/Library/Frameworks/Python.framework/Versions/%s/Python',
            u'/System/Library/Frameworks/Python.framework/Versions/%s/Python',
        ]],
    )
    pdict.update(plist)
    pythonInfo = pdict.setdefault(u'PythonInfoDict', {})
    pythonInfo.update(dict(
        PythonLongVersion=unicode(sys.version),
        PythonShortVersion=unicode(sys.version[:3]),
        PythonExecutable=unicode(sys.executable),
    ))
    py2pluginInfo = pythonInfo.setdefault(u'py2plugin', {}).update(dict(
        version=unicode(py2plugin.__version__),
        template=u'bundle',
    ))
    return pdict