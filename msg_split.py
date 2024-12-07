"""
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

Author Stepan Bakshaev, 2024.
Contact stepan.bakshaev@keemail.me
"""
from argparse import ArgumentParser
from enum import Enum
from itertools import chain
from operator import attrgetter, itemgetter
from typing import Iterator

from bs4 import BeautifulSoup
from bs4.element import Tag

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = frozenset("p b strong i ul ol div span".split(' '))  # ? | {BeautifulSoup.ROOT_TAG_NAME}


Automata = Enum('Automata', 'pull collect drain stop')


# XXX: I am tired of <object object at 0x77e9eff78e70>
Event = Enum('Event', ((name, getattr(Tag, name)) for name in 'START_ELEMENT_EVENT END_ELEMENT_EVENT EMPTY_ELEMENT_EVENT STRING_ELEMENT_EVENT'.split()))


def dump_element(element):
    if element is None:
        return None
    parents = [element.name]
    node = element.parent
    while node:
        parents.append(node.name)
        node = node.parent
    return '/'.join(map(str, reversed(parents)))


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""
    # The task is mess of implementation details (BeautifulSoup, html.parser), mistakes, obscures, and gaps
    # in the description, knowledge field, corner cases. But the core idea is simple.
    # All you have to do is to calculate minimal size of characters around piece you take from html
    # and push to fragment.
    # The implementation is built around idea to not add more complexity to time and space html parsing takes already.
    # There are dirty places of calling Tag._format_tag. I think nobody notice and we are here not dealing with C
    # and developing GTA 5 to get N².

    if max_len <= 1:
        raise ValueError(f'max_len argument ({max_len!r}) must be more then 0.', max_len)

    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        sourceline = None
        sourcepos = None
        raise UnprocessedValue(f'{sourceline}:{sourcepos}: source cannot be parsed.', sourceline, sourcepos) from e

    eventual_encoding = 'utf-8'
    formatter = soup.formatter_for_name('minimal')

    # State is about element from a stream to push in a fragment.
    events = soup._event_stream()
    sourceline = 0
    sourcepos = 0
    piece = ''
    event, element = None, None
    element_name = None
    weight = 0

    # State is about fragment.
    # size is minimal amount of characters to put element into fragment.
    size = 0
    # fragment_len is total amount of characters.
    fragment_len = 0
    # The word atom is derived from the ancient Greek word atomos, which means "uncuttable".
    # An index of uncuttable block tag.
    atomic_forward_index = -1
    atomic_backward_index = -1
    atomic_parent_index = -1
    # _prefix_sum accumulates occupied positions from fragment with max_len.
    forward = ['']
    forward_prefix_sum = [0]
    backward = ['']
    backward_prefix_sum = [0]
    # XXX: is it any sense of elements now?
    elements = [None]  # it is in sync with forward.
    parents = [None]
    parents_prefix_sum = [0]

    # State is about automata.
    state = Automata.pull
    # PULL resets track (0 value). Each other step increments track by 1.
    # 4       0    +1   +1    +1   +1
    # CYCLE = PULL_COLLECT_DRAIN_COLLECT_DRAIN
    PULL, PULL_COLLECT, PULL_COLLECT_DRAIN, PULL_COLLECT_DRAIN_COLLECT, CYCLE = range(5)
    track = PULL

    while state is not Automata.stop:
        assert len(forward) == len(forward_prefix_sum)
        assert len(forward) == len(elements), (forward, elements)
        assert len(backward) == len(backward_prefix_sum)
        assert len(parents) == len(parents_prefix_sum)

        if track == CYCLE:
            raise RuntimeError(f'{sourceline}:{sourcepos}: processing is in infinitive cycle.', sourceline, sourcepos)

        match state:
            case Automata.pull:
                pair = next(events, None)
                if pair is None:
                    state = Automata.stop

                else:
                    track = PULL
                    state = Automata.collect

                    tag_event, element = pair
                    if tag_event not in Event:
                        raise RuntimeError(f'{sourceline}:{sourcepos}: unhandled tag_event {tag_event!r}', sourceline, sourcepos, tag_event)
                    event = Event(tag_event)
                    element_name = element.name

                    if isinstance(element, Tag):
                        if element.sourceline is not None and element.sourceline > sourceline:
                            sourceline = element.sourceline
                        if element.sourcepos is not None and element.sourcepos > sourcepos:
                            sourcepos = element.sourcepos

            case Automata.collect:
                track += 1
                fragment_len = forward_prefix_sum[-1] + backward_prefix_sum[-1]
                match event:
                    case Event.START_ELEMENT_EVENT:
                        piece = element._format_tag(
                            eventual_encoding, formatter, opening=True
                        )
                        piece_end = element._format_tag(
                            eventual_encoding, formatter, opening=False
                        )
                        weight = len(piece) + len(piece_end)

                        if fragment_len + weight > max_len:
                            state = Automata.drain

                        else:
                            state = Automata.pull
                            if element.name not in split_tags:
                                # set length as value, because next step is append.
                                atomic_forward_index = len(forward)
                                atomic_backward_index = len(backward)
                                atomic_parent_index = len(parents)
                            forward.append(piece)
                            forward_prefix_sum.append(forward_prefix_sum[-1]+len(piece))
                            backward.append(piece_end)
                            backward_prefix_sum.append(backward_prefix_sum[-1]+len(piece_end))
                            elements.append(element)
                            parents.append(element)
                            parents_prefix_sum.append(parents_prefix_sum[-1]+weight)

                    # space for closing tag is reserved up front. It does not change sum.
                    case Event.END_ELEMENT_EVENT:
                        state = Automata.pull
                        forward.append(backward.pop())
                        forward_prefix_sum.append(forward_prefix_sum[-1]+backward_prefix_sum.pop()-backward_prefix_sum[-1])
                        elements.append(None)
                        parents.pop()
                        parents_prefix_sum.pop()
                        if len(parents) <= atomic_parent_index:
                            atomic_forward_index = -1
                            atomic_backward_index = -1
                            atomic_parent_index = -1

                    case Event.EMPTY_ELEMENT_EVENT | Event.STRING_ELEMENT_EVENT:
                        piece = element.output_ready(formatter=None)
                        weight = len(piece)
                        if fragment_len + weight > max_len:
                            state = Automata.drain

                        else:
                            state = Automata.pull
                            forward.append(piece)
                            forward_prefix_sum.append(forward_prefix_sum[-1]+weight)
                            elements.append(None)

                    case unhandled:
                        raise RuntimeError(f'{sourceline}:{sourcepos}: unhandled event {unhandled!r}.', sourceline, sourcepos, unhandled)

                if state is not Automata.drain:
                    if atomic_forward_index != -1:
                        # size is direct parent surround, self, content.
                        size_parent = parents_prefix_sum[atomic_parent_index]  # includes self
                        size_content = forward_prefix_sum[-1] - forward_prefix_sum[atomic_forward_index]
                        size = size_parent + size_content
                    else:
                        # size is only parents tags.
                        size = parents_prefix_sum[-1]

            case Automata.drain:
                if size + weight > max_len:
                    parents_tags = list(map(attrgetter("name"), parents[1:]))
                    raise UnprocessedValue(
                        f'{sourceline}:{sourcepos}: piece {piece[:38]!r} and html around {"/".join(parents_tags)} cannot fit max_len ({max_len}).',
                        sourceline, sourcepos, piece, parents_tags, max_len
                    )

                track += 1
                state = Automata.collect

                # remove chain of parent-first child from output, like "<p><strong><i><b>".
                # The algorithm does not account semantics. Means ['<ul>', '\n', '<li>'] produces ['<ul>', '\n'].
                parent = element.parent
                forward_skip_index = len(forward)
                backward_skip_index = len(backward)

                # ...but before pull atomic part.
                if atomic_forward_index != -1:
                    parent = elements[atomic_forward_index].parent
                    forward_skip_index = atomic_forward_index
                    backward_skip_index = atomic_backward_index

                # forward starts with ''
                for _ in range(forward_skip_index, 0, -1):
                    e = elements[forward_skip_index-1]
                    if e != parent:
                        break
                    forward_skip_index -= 1
                    backward_skip_index -= 1
                    parent = e.parent

                fragment = ''.join(chain(forward[:forward_skip_index], reversed(backward[:backward_skip_index])))
                assert len(fragment) <= max_len, ('Fragment length fits max_len', sourceline, sourcepos, fragment[:38], len(fragment), max_len)
                yield fragment

                descend = len(parents)
                leading = []
                leading_elements = []
                leading_prefix_sum = []
                if atomic_forward_index != -1:
                    leading = forward[atomic_forward_index+1:]
                    leading_elements = elements[atomic_forward_index+1:]
                    initial = forward_prefix_sum[atomic_forward_index]
                    leading_prefix_sum = [s - initial for s in forward_prefix_sum[atomic_forward_index+1:]]
                    descend = atomic_parent_index+1

                # backward stays the same.
                forward.clear()
                forward.append('')
                forward_prefix_sum.clear()
                forward_prefix_sum.append(0)
                elements.clear()
                elements.extend(parents[:descend])

                for index in range(1, descend):
                    # XXX: Should it be cached in parents_opening?
                    parent_piece = parents[index]._format_tag(
                        eventual_encoding, formatter, opening=True
                    )
                    forward.append(parent_piece)
                    forward_prefix_sum.append(parents_prefix_sum[index]-backward_prefix_sum[index])

                if atomic_forward_index != -1:
                    forward.extend(leading)
                    initial = forward_prefix_sum[-1]
                    forward_prefix_sum.extend(map(lambda s: s+initial, leading_prefix_sum))
                    elements.extend(leading_elements)

                fragment = None

    fragment = ''.join(chain(forward, backward))
    assert len(fragment) <= max_len, ('Fragment length fits max_len', sourceline, sourcepos, fragment[:38], len(fragment), max_len)
    yield fragment


def main(opts):
    with open(opts.source, 'rt') as stream:
        source = stream.read()

    for number, chunk in enumerate(split_message(source, max_len=opts.max_len), 1):
        fragmen_length = len(chunk)
        print(f'fragment #{number}: {fragmen_length} chars.')
        print(chunk)


if __name__ == '__main__':
    arguments = ArgumentParser(description='Split html message by chunks in max-len size.')
    arguments.add_argument('--max-len', type=int, default=MAX_LEN)
    arguments.add_argument('source', help='Path to source file.')

    main(arguments.parse_args())
