from msg_split import split_message, split_tags, UnprocessedValue
import pytest

def test_task_example():
    message = """\
<p>
    ... ... ...
    <b>
        ... ... ...
        <a href="https://www.google.com/">Google search</a>
        <ul>
            <li>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</li>
            <li>Ut enim ad minim veniam, quis nostrud exercitation ullamco.</li>
- - - Место разделения - - -
            <li>Duis aute irure dolor in reprehenderit in voluptate.</li>
        </ul>
    </b>
</p>
"""
    message_part_01 = """\
<p>
    ... ... ...
    <b>
        ... ... ...
        <a href="https://www.google.com/">Google search</a>
        <ul>
            <li>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</li>
            <li>Ut enim ad minim veniam, quis nostrud exercitation ullamco.</li>
        </ul>
    </b>
</p>
"""
    message_part_02 = """\
<p>
    <b>
        <ul>
            <li>Duis aute irure dolor in reprehenderit in voluptate.</li>
        </ul>
    </b>
</p>
"""
    max_length = len(message_part_01)

    parts = list(split_message(message, max_length))
    assert parts == [message_part_01, message_part_02], "Message is split successfully."


def test_undivided_tag():
    assert 'a' not in split_tags, 'Test is valid until <a> is not allowed to split.'
    message = '<a href="http://thelongestdomainnameintheworldandthensomeandthensomemoreandmore.com/">God\'s Final Message</a>'
    with pytest.raises(UnprocessedValue) as e_info:
        next(split_message(message, len(message)-1))
    assert e_info is None


@pytest.mark.parametrize(
    "message,result",
    [
        ('<a></p>', []),
        ('</table>', [])
    ],
)
def test_syntax_error_totally_fine_and_washed_out(message, result):
    assert list(split_message('</table>')) == result
