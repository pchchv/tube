"""Module for interacting with a user's youtube channel."""
from typing import Optional, Dict
from tube import extract, request
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

    @property
    def html(self):
        """Get the html for the /videos page.
        :rtype: str
        """
        if self._html:
            return self._html
        self._html = request.get(self.videos_url)
        return self._html

    @property
    def playlists_html(self):
        """Get the html for the /playlists page.
        Currently unused for any functionality.
        :rtype: str
        """
        if self._playlists_html:
            return self._playlists_html
        else:
            self._playlists_html = request.get(self.playlists_url)
            return self._playlists_html

    @property
    def community_html(self):
        """Get the html for the /community page.
        Currently unused for any functionality.
        :rtype: str
        """
        if self._community_html:
            return self._community_html
        else:
            self._community_html = request.get(self.community_url)
            return self._community_html

    @property
    def featured_channels_html(self):
        """Get the html for the /channels page.
        Currently unused for any functionality.
        :rtype: str
        """
        if self._featured_channels_html:
            return self._featured_channels_html
        else:
            self._featured_channels_html = request.get(
                self.featured_channels_url)
            return self._featured_channels_html

    @property
    def about_html(self):
        """Get the html for the /about page.
        Currently unused for any functionality.
        :rtype: str
        """
        if self._about_html:
            return self._about_html
        else:
            self._about_html = request.get(self.about_url)
            return self._about_html
