import sys
import os
from py2plugin import build_plugin

def main():
    build_plugin('pyplugin.py')
    os.system('xcodebuild')
    return 0

if __name__ == '__main__':
    sys.exit(main())
