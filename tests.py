import pytest

from msg_split import UnprocessedValue, split_message, split_tags


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
    assert list(split_message('\n'.join([fragment]*times), len(fragment)))


def test_do_not_leave_empty_parents():
    tag_name = sorted(iter(split_tags))[0]
    fragment = f'<{tag_name}>Hello, World!</{tag_name}>'
    times = 3
    assert list(split_message('\n'.join([fragment]*times), len(fragment))) == [fragment] +['\n', fragment]*(times-1)


def test_blank_nested_do_not_fit():
    tag_name = sorted(iter(split_tags))[0]
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
I would like to make a case with outer atomic tag and inside decomposable content.</p>
""",
"""<p><a href="https://www.linkedin.com/in/stepan-bakshaev/">Link to <strong>Author</strong> of <b>the source code</b>.</a>
</p>
"""
    ]


def test_split_tags_1():
    assert 'li' not in split_tags, 'Pre-requirements.'
    assert 'p' in split_tags, 'Pre-requirements.'
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
</p>
""",
"""<p><ul>
    <li>there is no <strong>GIL</strong></li>
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
