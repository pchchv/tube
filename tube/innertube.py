"""This module is designed to interact with the innertube API.
This module is NOT intended for direct use by end users,
since each of the interfaces return raw results.
Instead, they should be parsed to extract useful information for the end user.
"""

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
