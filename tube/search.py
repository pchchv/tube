"""Module for interacting with YouTube search."""
from tube.innertube import InnerTube


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
        """Getting raw results from API innertube.
        :param str continuation: The continuation string for getting results.
        :rtype: dict
        :returns: Unprocessed json object returned by the innertube API.
        """
        query_results = self._innertube_client.search(self.query, continuation)
        if not self._initial_results:
            self._initial_results = query_results
        return query_results  # noqa:R504
