from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('girder-cli-oauth-client')
except PackageNotFoundError:
    # package is not installed
    pass

from .client import GirderCliOAuthClient

__all__ = ['GirderCliOAuthClient']
