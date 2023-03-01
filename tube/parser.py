import ast
import json
from tube.exceptions import HTMLParseError


def parse_for_object_from_startpoint(html, start_point):
    """JSONifies an object parsed from HTML.
    :param str html: HTML to be parsed for the object.
    :param int start_point: The start index of the object.
    :rtype dict:
    :return: The dict created by parsing the object.
    """
    full_obj = find_object_from_startpoint(html, start_point)
    try:
        return json.loads(full_obj)
    except json.decoder.JSONDecodeError:
        try:
            return ast.literal_eval(full_obj)
        except (ValueError, SyntaxError):
            raise HTMLParseError('Could not parse object.')


def find_object_from_startpoint(html, start_point):
    """Parses the input html to find the end of the JavaScript object.
    :param str html: HTML to parse the object.
    :param int start_point: The index of the start of the object.
    :rtype dict:
    :return: The dict created by parsing the object.
    """
    html = html[start_point:]
    if html[0] not in ['{', '[']:
        raise HTMLParseError(f'Invalid start point. \
                             Start of HTML:\n{html[:20]}')

    # The first letter MUST be an open parenthesis,
    # so we put it on the stack and skip the first character.
    stack = [html[0]]
    i = 1

    context_closers = {
        '{': '}',
        '[': ']',
        '"': '"'
    }

    while i < len(html):
        if len(stack) == 0:
            break
        curr_char = html[i]
        curr_context = stack[-1]

        # When approaching a context, can remove an element from the stack
        if curr_char == context_closers[curr_context]:
            stack.pop()
            i += 1
            continue

        # Strings require special context handling because they can
        # contain context opening and context closing elements
        if curr_context == '"':
            # If there's a backslash in a string, skip a character
            if curr_char == '\\':
                i += 2
                continue
        else:
            # Non-string contexts are when need to look for context openers.
            if curr_char in context_closers.keys():
                stack.append(curr_char)

        i += 1

    full_obj = html[:i]
    return full_obj  # noqa: R504
