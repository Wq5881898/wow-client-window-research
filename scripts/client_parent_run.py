"""The identity of the task that started a step.

The standard acceptance runs several scripts one after another. A result
that belongs to another attempt must not be taken for the result of this
one, so the parent hands every step an identifier of its own, and the step
writes that identifier into its result. The parent then checks that the
result carries the identifier it handed out.

Without this, a result file that is left over from an earlier run can be
picked up as the result of the current one, which is the mistake the
review named under ACC-02.
"""


def parent_of(argv):
    """The identifier of the parent task, or None when there is none."""
    for index, word in enumerate(argv):
        if word == '--parent-run' and index + 1 < len(argv):
            return argv[index + 1]
    return None


def attempt_of(argv):
    """The number of the attempt of the parent task, or None."""
    for index, word in enumerate(argv):
        if word == '--attempt' and index + 1 < len(argv):
            try:
                return int(argv[index + 1])
            except ValueError:
                return None
    return None


def stamp(result, argv):
    """Write the identity of the parent task into the result of a step."""
    parent = parent_of(argv)
    if parent:
        result['parent_run'] = parent
    attempt = attempt_of(argv)
    if attempt is not None:
        result['parent_attempt'] = attempt
    return result
