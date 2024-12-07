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
        if track == CYCLE:
            raise RuntimeError(f'{sourceline}:{sourcepos}: processing is in infinitive cycle.', sourceline, sourcepos)

        if __debug__:
            print(f'{state=!s} <=')
            print(f'\t{size=}/{fragment_len=} ? {max_len=}')
            if state is not Automata.pull:
                print(f'\t{event=!s} {element_name=}')
                print(f'\tpath={dump_element(element)}')

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
                        forward_prefix_sum.append(backward_prefix_sum.pop()-backward_prefix_sum[-1])
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
                        raise NotImplementedError
                    else:
                        # size is only parents tags.
                        size = parents_prefix_sum[-1]

                    fragment_len = forward_prefix_sum[-1] + backward_prefix_sum[-1]

            case Automata.drain:
                if size + weight > max_len:
                    parents_tags = list(map(attrgetter("name"), map(itemgetter(0), parents)))
                    raise UnprocessedValue(
                        f'{sourceline}:{sourcepos}: piece {piece[:38]!r} and html around {"/".join(parents_tags)} cannot fit max_len ({max_len}).',
                        sourceline, sourcepos, piece, parents_tags, max_len
                    )

                track += 1
                state = Automata.collect

                if atomic_forward_index != -1:
                    raise NotImplementedError

                # skip chain of parent-first child from output, like "<p><strong><i><b>".

                forward_index = len(forward)
                backward_index = len(backward)
                parent = element.parent

                parents_tags = list(map(attrgetter("name"), map(itemgetter(0), parents)))
                print(f'{atomic_index=} {parents_tags=} {forward=} {forward_index=} {backward=} {backward_index=} parent={dump_element(parent)}')

                if atomic_index < len(parents):
                    atomic_element = parents[atomic_index][0]
                    parent = atomic_element.parent
                    backward_index -= len(parents) - atomic_index
                    print(f'atomic_element={dump_element(atomic_element)}')
                    while elements[forward_index-1] != atomic_element:
                        forward_index -= 1
                    forward_index -= 1

                print(f'{forward_index=} parent={dump_element(parent)}')
                while forward_index > 0 and elements[forward_index-1] == parent:
                    parent = elements[forward_index-1]
                    forward_index -= 1
                    backward_index -= 1

                fragment = ''.join(chain(forward[:forward_index], reversed(backward[:backward_index])))
                print(f'{forward_index=} {backward_index=} {fragment=}')
                assert len(fragment) <= max_len, ('Fragment length fits max_len', sourceline, sourcepos, fragment[:38], len(fragment), max_len)
                yield fragment

                budget = 0
                leading_pieces = forward[forward_index:]
                leading_elements = elements[forward_index:]
                descend = backward_index
                forward.clear()
                elements.clear()
                for parent, weight in parents[:descend]:
                    parent_piece = parent._format_tag(
                        eventual_encoding, formatter, opening=True
                    )
                    forward.append(parent_piece)
                    elements.append(parent)

                forward.extend(leading_pieces)
                elements.extend(leading_elements)

                print(f'{fragment=}')
                print('---')
                fragment = None

        if __debug__:
            print('')

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
