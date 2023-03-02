"""This module is designed to interact with the innertube API.
This module is NOT intended for direct use by end users,
since each of the interfaces return raw results.
Instead, they should be parsed to extract useful information for the end user.
"""
import os
import pathlib

# YouTube on TV client secrets
_client_id = ''  # TODO: Add env variables
_client_secret = ''  # TODO: Add env variables

# Extracted API keys -- unclear what these are linked to.
_api_keys = ['', '', '', '', '', '']  # TODO: Add env variables

_default_clients = {
    'WEB': {
        'context': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20200720.00.02'
            }
        },
        'api_key': ''  # TODO: Add env variables
    },
    'ANDROID': {
        'context': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '16.20'
            }
        },
        'api_key': ''  # TODO: Add env variables
    },
    'WEB_EMBED': {
        'context': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20210721.00.00',
                'clientScreen': 'EMBED'
            }
        },
        'api_key': ''  # TODO: Add env variables
    },
    'ANDROID_EMBED': {
        'context': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '16.20',
                'clientScreen': 'EMBED'
            }
        },
        'api_key': ''  # TODO: Add env variables
    }
}
_token_timeout = 1800
_cache_dir = pathlib.Path(__file__).parent.resolve() / '__cache__'
_token_file = os.path.join(_cache_dir, 'tokens.json')


class InnerTube:
    """Object for interacting with the innertube API."""
    def __init__(self, client='ANDROID', use_oauth=False, allow_cache=True):
        """Initialize an InnerTube object.
        :param str client: Client to use for the object.
            Default to web because it returns the most playback types.
        :param bool use_oauth: Whether or not to authenticate to YouTube.
        :param bool allow_cache: Allows caching of oauth tokens on the machine.
        """
        self.context = _default_clients[client]['context']
        self.api_key = _default_clients[client]['api_key']
        self.access_token = None
        self.refresh_token = None
        self.use_oauth = use_oauth
        self.allow_cache = allow_cache
        # Stored as epoch time
        self.expires = None

        # Try to load from file if specified
        if self.use_oauth and self.allow_cache:
            # Try to load from file if possible
            if os.path.exists(_token_file):
                with open(_token_file) as f:
                    data = json.load(f)
                    self.access_token = data['access_token']
                    self.refresh_token = data['refresh_token']
                    self.expires = data['expires']
                    self.refresh_bearer_token()
