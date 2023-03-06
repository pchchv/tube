"""Module for interacting with a user's youtube channel."""
from tube import extract
from typing import Optional, Dict
from tube.playlist import Playlist


class Channel(Playlist):
    def __init__(self, url: str, proxies: Optional[Dict[str, str]] = None):
        """Construct :class:`Channel <Channel>`.
        :param str url: The actual URL of the YouTube channel.
        :param proxies: (Optional) Dictionary of proxies used for web requests.
        """
        super().__init__(url, proxies)

        self.channel_uri = extract.channel_name(url)

        self.channel_url = (
            f"https://www.youtube.com{self.channel_uri}"
        )

        self.videos_url = self.channel_url + '/videos'
        self.playlists_url = self.channel_url + '/playlists'
        self.community_url = self.channel_url + '/community'
        self.featured_channels_url = self.channel_url + '/channels'
        self.about_url = self.channel_url + '/about'

        # Possible future additions
        self._playlists_html = None
        self._community_html = None
        self._featured_channels_html = None
        self._about_html = None

    @property
    def channel_name(self):
        """Get the name of the YouTube channel.
        :rtype: str
        """
        return self.initial_data['metadata'][
            'channelMetadataRenderer']['title']

    @property
    def channel_id(self):
        """Get the ID of the YouTube channel.
        This will return the underlying ID, not the vanity URL.
        :rtype: str
        """
        return self.initial_data['metadata'][
            'channelMetadataRenderer']['externalId']

    @property
    def vanity_url(self):
        """Get the vanity URL of the YouTube channel.
        Returns None if it doesn't exist.
        :rtype: str
        """
        return self.initial_data['metadata'][
            'channelMetadataRenderer'].get('vanityChannelUrl', None)
