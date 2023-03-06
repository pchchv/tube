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
