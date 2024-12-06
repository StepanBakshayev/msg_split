import pytest

from msg_split import UnprocessedValue, split_message, split_tags


@pytest.mark.skip('waiting for implementation')
def test_garbage_in_undefined_out():
    # XXX: sourceline+sourcepos could help to preserve original string, but I do not believe it is enough.
    # I think custom parser is required to reproduce malformed html in output.
    message = '<a><b /></a>'
    result = '<a><b></b></a>'
    assert list(split_message(message, len(result))) == [result]


def test_empy():
    assert list(split_message('', 38)) == ['']


def test_tag_exceeded():
    message = '<b></b>'
    with pytest.raises(UnprocessedValue):
        assert list(split_message(message, len(message)-1))


def test_straight_forward():
    tag_name = sorted(iter(split_tags))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message(''.join([fragment]*times), len(fragment))) == [fragment]*times


def test_do_not_cycle():
    tag_name = sorted(iter(split_tags))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message('\n'.join([fragment]*times), len(fragment))) == [fragment]*times
