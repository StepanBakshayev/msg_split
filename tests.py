"""
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

Author Stepan Bakshaev, 2024.
Contact stepan.bakshaev@keemail.me
"""
import pytest
from bs4 import BeautifulSoup

from msg_split import UnprocessedValue, split_message, split_tags

# XXX: html.parser squashes spaces in some cases to new line. Do not use spaces in original message for indentation.

def test_garbage_in_undefined_out():
    # XXX: sourceline+sourcepos could help to preserve original string, but I do not believe it is enough.
    # I think custom parser is required to reproduce malformed html in output.
    message = '<a><b /></a>'
    result = '<a><b></b></a>'
    # if message is equal or less than max_len result is untouched.
    assert list(split_message(message, len(message))) == [message]


def test_empy():
    assert list(split_message('', 38)) == ['']


def test_tag_exceeded():
    message = '<b></b>'
    with pytest.raises(UnprocessedValue):
        assert list(split_message(message, len(message)-1))


def test_straight_forward():
    tag_name = sorted(iter(split_tags-{BeautifulSoup.ROOT_TAG_NAME}))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message(''.join([fragment]*times), len(fragment))) == [fragment]*times


def test_do_not_cycle():
    tag_name = sorted(iter(split_tags-{BeautifulSoup.ROOT_TAG_NAME}))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message('\n'.join([fragment]*times), len(fragment)))


def test_do_not_leave_empty_parents():
    tag_name = sorted(iter(split_tags-{BeautifulSoup.ROOT_TAG_NAME}))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message('\n'.join([fragment]*times), len(fragment))) == [fragment] +['\n', fragment]*(times-1)


def test_blank_nested_do_not_fit():
    tag_name = sorted(iter(split_tags-{BeautifulSoup.ROOT_TAG_NAME}))[0]
    message = f'<{tag_name}><{tag_name}><{tag_name}></{tag_name}></{tag_name}></{tag_name}>'
    with pytest.raises(UnprocessedValue):
        assert list(split_message(message, max_len=len(message)-1))


def test_split_example():
    assert {'span', 'div'} <= split_tags, 'Used tags are in split registry.'
    message = (
"""<strong>Done</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12427"><code>ABC-12427</code></a> Fusce cursus euismod ligula nec ullamcorper.
<a href="https://mockdata.atlassian.net/browse/ABC-12452"><code>ABC-12452</code></a> Nam vulputate feugiat.
<a href="https://mockdata.atlassian.net/browse/ABC-12513"><code>ABC-12513</code></a> Sem, eu cursus neque interdum ac.
<a href="https://mockdata.atlassian.net/browse/ABC-12580"><code>ABC-12580</code></a> Nulla sodales libero eu lectus gravida varius.

Christan Van der Kruys
<strong>In progress</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12503"><code>ABC-12503</code></a> In sem libero, lobortis eu posuere quis, iaculis sed.

<strong>Done</strong>
<span>
<p>test</p>
<a href="https://mockdata.atlassian.net/browse/ABC-11872"><code>ABC-11872</code></a> Etiam cursus nisi eget tortor feugiat.
<a href="https://mockdata.atlassian.net/browse/ABC-12129"><code>ABC-12129</code></a> Non congue tortor cursus.
<div>
<a href="https://mockdata.atlassian.net/browse/ABC-12354"><code>ABC-12354</code></a> Ut finibus urna sed lorem elementum.
<a href="https://mockdata.atlassian.net/browse/ABC-12398"><code>ABC-12398</code></a> Eget tristique magna vulputate.
<a href="https://mockdata.atlassian.net/browse/ABC-12455"><code>ABC-12455</code></a> Sed a orci at turpis commodo semper quis vitae erat.
<a href="https://mockdata.atlassian.net/browse/ABC-12522"><code>ABC-12522</code></a> Quis purus et augue varius egestas
</div>
<a href="https://mockdata.atlassian.net/browse/ABC-12538"><code>ABC-12538</code></a> Aliquam ac sollicitudin neque.
</span>
Millie Isaksson
<strong>In progress</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12062"><code>ABC-12062</code></a> Duis rhoncus venenatis risus in mollis.

""")
    assert list(split_message(message, 1107+6+7+1)) == [
"""<strong>Done</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12427"><code>ABC-12427</code></a> Fusce cursus euismod ligula nec ullamcorper.
<a href="https://mockdata.atlassian.net/browse/ABC-12452"><code>ABC-12452</code></a> Nam vulputate feugiat.
<a href="https://mockdata.atlassian.net/browse/ABC-12513"><code>ABC-12513</code></a> Sem, eu cursus neque interdum ac.
<a href="https://mockdata.atlassian.net/browse/ABC-12580"><code>ABC-12580</code></a> Nulla sodales libero eu lectus gravida varius.

Christan Van der Kruys
<strong>In progress</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12503"><code>ABC-12503</code></a> In sem libero, lobortis eu posuere quis, iaculis sed.

<strong>Done</strong>
<span>
<p>test</p>
<a href="https://mockdata.atlassian.net/browse/ABC-11872"><code>ABC-11872</code></a> Etiam cursus nisi eget tortor feugiat.
<a href="https://mockdata.atlassian.net/browse/ABC-12129"><code>ABC-12129</code></a> Non congue tortor cursus.
<div>
<a href="https://mockdata.atlassian.net/browse/ABC-12354"><code>ABC-12354</code></a> Ut finibus urna sed lorem elementum.
</div></span>""",
"""<span><div><a href="https://mockdata.atlassian.net/browse/ABC-12398"><code>ABC-12398</code></a> Eget tristique magna vulputate.
<a href="https://mockdata.atlassian.net/browse/ABC-12455"><code>ABC-12455</code></a> Sed a orci at turpis commodo semper quis vitae erat.
<a href="https://mockdata.atlassian.net/browse/ABC-12522"><code>ABC-12522</code></a> Quis purus et augue varius egestas
</div>
<a href="https://mockdata.atlassian.net/browse/ABC-12538"><code>ABC-12538</code></a> Aliquam ac sollicitudin neque.
</span>
Millie Isaksson
<strong>In progress</strong>
<a href="https://mockdata.atlassian.net/browse/ABC-12062"><code>ABC-12062</code></a> Duis rhoncus venenatis risus in mollis.

"""
    ]


def test_split_tags_2():
    assert 'a' not in split_tags, 'Pre-requirements.'
    assert 'p' in split_tags, 'Pre-requirements.'
    message = (
"""\
<p>
I would like to make a case with outer atomic tag and inside decomposable content.
<a href="https://www.linkedin.com/in/stepan-bakshaev/">Link to <strong>Author</strong> of <b>the source code</b>.</a>
</p>
"""
    )
    assert list(split_message(message, 180)) == [
"""\
<p>
I would like to make a case with outer atomic tag and inside decomposable content.
</p>""",
"""<p><a href="https://www.linkedin.com/in/stepan-bakshaev/">Link to <strong>Author</strong> of <b>the source code</b>.</a>
</p>
"""
    ]


def test_split_tags_1_collapse_nested_without_semantic():
    assert 'li' not in split_tags, 'Pre-requirements.'
    assert {'p', 'ul', 'strong', 'i'} <= split_tags, 'Pre-requirements.'
    message = (
"""\
<p>
Ocaml is the best language for business projects. There are advantages:
<ul>
<li>there is no <strong>GIL</strong></li>
<li><i>soundness</i> type system</li>
</ul>
</p>
"""
    )
    assert list(split_message(message, 111)) == [
"""\
<p>
Ocaml is the best language for business projects. There are advantages:
<ul>
</ul></p>""",
"""<p><ul><li>there is no <strong>GIL</strong></li>
<li><i>soundness</i> type system</li>
</ul>
</p>
"""
    ]


def test_nested():
    message = '<p>Hello!<b><i><strong>World</strong></i></b>!</p>'
    assert list(split_message(message, 44)) == [
        '<p>Hello!</p>',
        '<p><b><i><strong>World</strong></i></b>!</p>'
    ]
