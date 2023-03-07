"""Module for interacting with YouTube search."""
import logging
from utube import YouTube
from utube.innertube import InnerTube


logger = logging.getLogger(__name__)


class Search:
    def __init__(self, query):
        """Initialize Search object.
        :param str query: Search query provided by the user.
        """
        self.query = query
        self._innertube_client = InnerTube(client='WEB')

        # The first search, without continuation,
        # is structured differently and contains suggestions for completion,
        # so it is necessary to store it separately
        self._initial_results = None

        self._results = None
        self._completion_suggestions = None

        # Used to keep track of the query continuation,
        # so that new results are always returned when
        # get_next_results() is called
        self._current_continuation = None

    @property
    def completion_suggestions(self):
        """Returns auto-complete query sentences.
        :rtype: list
        :returns: The list of autocomplete suggestions provided by
            YouTube for this request.
        """
        if self._completion_suggestions:
            return self._completion_suggestions
        if self.results:
            self._completion_suggestions = self._initial_results['refinements']
        return self._completion_suggestions

    @property
    def results(self):
        """Returns the results of the search.
        The first call generates and returns the first set of results.
        Additional results can be retrieved with ``.get_next_results()``.
        :rtype: list
        :returns: A list of YouTube objects.
        """
        if self._results:
            return self._results

        videos, continuation = self.fetch_and_parse()
        self._results = videos
        self._current_continuation = continuation
        return self._results

    def get_next_results(self):
        """Use the saved continuation string to get the next set of results.
        This method does not return results, but updates the results property.
        """
        if self._current_continuation:
            videos, continuation = \
                self.fetch_and_parse(self._current_continuation)
            self._results.extend(videos)
            self._current_continuation = continuation
        else:
            raise IndexError

    def fetch_query(self, continuation=None):
        """Fetching raw results from API innertube.
        :param str continuation: The continuation string for getting results.
        :rtype: dict
        :returns: Unprocessed json object returned by the innertube API.
        """
        query_results = self._innertube_client.search(self.query, continuation)
        if not self._initial_results:
            self._initial_results = query_results
        return query_results  # noqa:R504

    def fetch_and_parse(self, continuation=None):
        """Fetching data from API innertube and parsing results.
        :param str continuation: continuation string to get results.
        :rtype: tuple
        :return:
            tuple from the list of YouTube objects and continuation string.
        """
        # Start by running the query and identifying the
        # appropriate sections of the results
        raw_results = self.fetch_query(continuation)

        # The initial result is handled by the try block,
        # and the continuation is handled by the except block.
        try:
            sections = raw_results['contents'][
                'twoColumnSearchResultsRenderer']['primaryContents'][
                'sectionListRenderer']['contents']
        except KeyError:
            sections = raw_results['onResponseReceivedCommands'][0][
                'appendContinuationItemsAction']['continuationItems']
        item_renderer = None
        continuation_renderer = None
        for s in sections:
            if 'itemSectionRenderer' in s:
                item_renderer = s['itemSectionRenderer']
            if 'continuationItemRenderer' in s:
                continuation_renderer = s['continuationItemRenderer']

        # If the continuationItemRenderer does not exist,
        # assume that there are no further results
        if continuation_renderer:
            next_continuation = continuation_renderer['continuationEndpoint'][
                'continuationCommand']['token']
        else:
            next_continuation = None

        # If itemSectionRenderer does not exist,
        # consider that there are no results.
        if item_renderer:
            videos = []
            raw_video_list = item_renderer['contents']
            for video_details in raw_video_list:
                # Skip over ads
                if video_details.get('searchPyvRenderer', {}).get('ads', None):
                    continue

                # Skip "recommended" videos, such as "people also watched" and
                # "popular X" videos, which break up search results
                if 'shelfRenderer' in video_details:
                    continue

                # Skip auto-generated "mix" playlist results
                if 'radioRenderer' in video_details:
                    continue

                # Skip playlist results
                if 'playlistRenderer' in video_details:
                    continue

                # Skip channel results
                if 'channelRenderer' in video_details:
                    continue

                # Skip 'people also searched for' results
                if 'horizontalCardListRenderer' in video_details:
                    continue

                # Unable to reproduce,
                # perhaps related to suggestions for correcting typos.
                if 'didYouMeanRenderer' in video_details:
                    continue

                # This appears to be the renderer used for the
                # image shown on the no results page
                if 'backgroundPromoRenderer' in video_details:
                    continue

                if 'videoRenderer' not in video_details:
                    logger.warn('Unexpected renderer encountered.')
                    logger.warn(f'Renderer name: {video_details.keys()}')
                    logger.warn(f'Search term: {self.query}')
                    logger.warn(
                        'Please open an issue at '
                        'https://github.com/pchchv/utube/issues '
                        'and provide this log output.'
                    )
                    continue

                # Extract relevant information about the
                # video from the details. Some of these can be used to
                # pre-fill the attributes of a YouTube object.
                vid_renderer = video_details['videoRenderer']
                vid_id = vid_renderer['videoId']
                vid_url = f'https://www.youtube.com/watch?v={vid_id}'
                vid_title = vid_renderer['title']['runs'][0]['text']
                vid_channel_name = vid_renderer['ownerText']['runs'][0]['text']
                vid_channel_uri = vid_renderer['ownerText']['runs'][0][
                    'navigationEndpoint']['commandMetadata'][
                    'webCommandMetadata']['url']
                # Livestreams have "runs", non-livestreams have "simpleText",
                #  and scheduled releases do not have 'viewCountText'
                if 'viewCountText' in vid_renderer:
                    if 'runs' in vid_renderer['viewCountText']:
                        vid_view_count_text = vid_renderer[
                            'viewCountText']['runs'][0]['text']
                    else:
                        vid_view_count_text = vid_renderer[
                            'viewCountText']['simpleText']
                    # Strip ' views' text, then remove commas
                    stripped_text = \
                        vid_view_count_text.split()[0].replace(',', '')
                    if stripped_text == 'No':
                        vid_view_count = 0
                    else:
                        vid_view_count = int(stripped_text)
                else:
                    vid_view_count = 0
                if 'lengthText' in vid_renderer:
                    vid_length = vid_renderer['lengthText']['simpleText']
                else:
                    vid_length = None

                vid_metadata = {
                    'id': vid_id,
                    'url': vid_url,
                    'title': vid_title,
                    'channel_name': vid_channel_name,
                    'channel_url': vid_channel_uri,
                    'view_count': vid_view_count,
                    'length': vid_length
                }

                # Construct YouTube object from metadata and append to results
                vid = YouTube(vid_metadata['url'])
                vid.author = vid_metadata['channel_name']
                vid.title = vid_metadata['title']
                videos.append(vid)
        else:
            videos = None

        return videos, next_continuation
