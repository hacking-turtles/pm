import os

import ida_loader
import idaapi

from pkg.virtualenv_utils import prepare_virtualenv
from pkg.package import LocalPackage, InstallablePackage
from pkg.logger import logger
from pkg.util import putenv

from . import __version__

RC = """
def init_idapkg():
    "idapythonrc.py is a perfect place to initialize IDAUSR variable"
    import os
    import sys
    import json

    def usage():
        print "idapkg is not installed or corrupted."
        print "please use the installation script below:"
        print "https://github.com/Jinmo/idapkg"

    basedir = os.path.expanduser(os.path.join('~', 'idapkg'))
    config = os.path.join(basedir, 'config.json')

    if os.path.isfile(config):
        try:
            with open(config, 'rb') as f:
                j = json.load(f)

            packages_path = j['path']['packages']
            idapkg_path   = os.path.join(packages_path, 'idapkg')
            assert os.path.isdir(idapkg_path), "idapkg package does not exist"
            # idapkg doesn't have any plugins. just load to path.
            # XXX: replace this with some package-related routines

            sys.path.append(idapkg_path)
            from pkg.main import init_environment
            init_environment()
        except:
            import traceback
            traceback.print_exc()
            return usage()
    else:
        return usage()

init_idapkg()
del init_idapkg
"""

SEP = '\n# idapkg version: ', '# idapkg end\n'


def update_pythonrc():
    rcpath = os.path.join(idaapi.get_user_idadir(), "idapythonrc.py")
    sep_with_ver = SEP[0] + __version__
    payload = '%s\n%s\n%s' % (sep_with_ver, RC.strip(), SEP[1])
    if os.path.isfile(rcpath):
        with open(rcpath, 'rb') as f:
            py = f.read()
            if payload in py:
                return

            if all(x in py for x in SEP):
                py = py.split(SEP[0], 1)
                py = py[0] + py[1].split(SEP[1], 1)[1]
            py = payload + py
            print('Updating idapkg into idapythonrc.py.')
    else:
        py = payload
        print('Added idapkg into idapythonrc.py. Will work after restarting!')

    with open(rcpath, 'wb') as f:
        f.write(py)


def init_environment(load=True):
    """
    Must be called from idapythonrc.py. I didn't test other cases.
    """
    logger.info("idapkg version %s" % __version__)
    prepare_virtualenv(wait=True)

    _initial_deps = ['ifred']
    _original_idausr = os.getenv('IDAUSR', '')

    if all(LocalPackage.by_name(_dep) for _dep in _initial_deps):
        for _dep in _initial_deps:
            LocalPackage.by_name(_dep) \
                ._find_loadable_modules('plugins', ida_loader.load_plugin)

    else:
        logger.info("Downloading initial dependencies...")
        logger.info("IDA must be restarted after printing \"Done!\"")
        print LocalPackage.all()

        for _dep in _initial_deps:
            InstallablePackage \
                .install_from_repo(Repository('https://api.idapkg.com'), _dep)

    if not load:
        return

    for pkg in LocalPackage.all():
        pkg.populate_env()

    import pkg.actions
    import pkg.hooks

    pkg.hooks.init_hooks(_original_idausr)

    from pkg.internal_api import invalidate_idausr
    invalidate_idausr()
