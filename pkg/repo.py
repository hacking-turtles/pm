import json
import traceback
import urllib
from StringIO import StringIO
from multiprocessing.pool import ThreadPool

from .package import InstallablePackage, LocalPackage
from .config import g
from .downloader import _download, MAX_CONCURRENT
from .logger import getLogger

TIMEOUT = 8
log = getLogger(__name__)


class Repository(object):
    """
    An instance of this class represents a single repository.
    """

    def __init__(self, url, timeout=TIMEOUT):
        self.url = url
        self.timeout = timeout

    def single(self, name):
        """
        Fetch metadata for single package from the repo.

        :returns: None if package is not found,
          else a :class:`~pkg.package.InstallablePackage` object
        :rtype: pkg.package.InstallablePackage or None
        """
        endpoint = '/info'
        res = _download(self.url + endpoint + '?id=' +
                        urllib.quote(name), self.timeout)
        if not res:  # Network Error
            return
        else:
            res = json.load(res)
            if not res['success']:
                return
            else:
                item = res['data']
                return InstallablePackage(
                    name=item['name'], id=item['id'], version=item['version'], repo=self)

    def list(self):
        """
        Fetch a list of all packages in the repo.

        :returns: list of InstallablePackage in the repo.
        :rtype: list(pkg.package.InstallablePackage)
        """
        endpoint = '/search'
        res = _download(self.url + endpoint, self.timeout)
        try:
            if res is None:
                raise Exception('connection error')

            res = json.load(res)
            assert isinstance(res['data'], list)

            # Only list non-installed packages
            return [
                InstallablePackage(
                    name=item['name'], id=item['id'], version=item['version'], repo=self)
                for item in res['data'] if LocalPackage.by_name(item['id']) is None
            ]
        except ValueError:
            string_io = StringIO()
            traceback.print_exc(file=string_io)
            log.error('Error fetching repo: %r\n%s',
                      self.url, string_io.getvalue())

    @staticmethod
    def from_urls(repos=None):
        if repos is None:
            repos = g['repos']

        repos = [Repository(repo) if isinstance(
            repo, basestring) else repo for repo in repos]
        return repos

    def __repr__(self):
        return "<Repository url=%r>" % self.url


def get_online_packages(repos=None):
    """
    Generates a list of packages from specified repositories.

    :param repos: Array of repository urls (string). Default: g['repos']
    :returns: Array of :class:`~pkg.package.InstallablePackage` pointing valid repos.
    """

    repos = Repository.from_urls()

    pool = ThreadPool(MAX_CONCURRENT)
    results = pool.map(lambda repo: repo.list(), repos)
    results = [x for x in results if x]

    # flatten results
    return [pkg for pkgs in results for pkg in pkgs]


if __name__ == '__main__':
    print '\n'.join(map(repr, get_online_packages()))
