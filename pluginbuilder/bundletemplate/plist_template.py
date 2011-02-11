import sys
from .. import __version__

def infoPlistDict(CFBundleExecutable, plist={}):
    CFBundleExecutable = str(CFBundleExecutable)
    NSPrincipalClass = ''.join(CFBundleExecutable.split())
    version = sys.version[:3]
    pdict = dict(
        CFBundleDevelopmentRegion='English',
        CFBundleDisplayName=plist.get('CFBundleName', CFBundleExecutable),
        CFBundleExecutable=CFBundleExecutable,
        CFBundleIconFile=CFBundleExecutable,
        CFBundleIdentifier='org.pythonmac.unspecified.%s' % (NSPrincipalClass,),
        CFBundleInfoDictionaryVersion='6.0',
        CFBundleName=CFBundleExecutable,
        CFBundlePackageType='BNDL',
        CFBundleShortVersionString=plist.get('CFBundleVersion', '0.0'),
        CFBundleSignature='????',
        CFBundleVersion='0.0',
        LSHasLocalizedDisplayName=False,
        NSAppleScriptEnabled=False,
        NSHumanReadableCopyright='Copyright not specified',
        NSMainNibFile='MainMenu',
        NSPrincipalClass=NSPrincipalClass,
        PyMainFileNames=['__boot__'],
        PyResourcePackages=[ (s % version) for s in [
            'lib/python%s',
            'lib/python%s/lib-dynload',
            'lib/python%s/site-packages.zip',
        ]] + [ 'lib/python%s.zip' % version.replace('.', '') ],
        PyRuntimeLocations=[(s % version) for s in [
            '@executable_path/../Frameworks/Python.framework/Versions/%s/Python',
            '~/Library/Frameworks/Python.framework/Versions/%s/Python',
            '/Library/Frameworks/Python.framework/Versions/%s/Python',
            '/Network/Library/Frameworks/Python.framework/Versions/%s/Python',
            '/System/Library/Frameworks/Python.framework/Versions/%s/Python',
        ]],
    )
    pdict.update(plist)
    pythonInfo = pdict.setdefault('PythonInfoDict', {})
    pythonInfo.update(dict(
        PythonLongVersion=str(sys.version),
        PythonShortVersion=str(sys.version[:3]),
        PythonExecutable=str(sys.executable),
    ))
    pythonInfo.setdefault('pluginbuilder', {}).update(dict(version=__version__))
    return pdict
