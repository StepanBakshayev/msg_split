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


Automata = Enum('Automata', 'pull push drain stop')


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
    return '/'.join(reversed(parents))


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""

    if max_len <= 1:
        raise ValueError(f'max_len argument ({max_len!r}) must be more then 0.', max_len)

    sourceline = 0
    sourcepos = 0

    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        raise UnprocessedValue(f'{sourceline}:{sourcepos}: source cannot be parsed.', sourceline, sourcepos) from e

    eventual_encoding = 'utf-8'
    formatter = soup.formatter_for_name('minimal')

    budget = 0
    piece = ''
    event, element = None, None
    element_name = None
    weight = 0
    forward = []
    elements = []
    backward = []
    atomic_index = 0
    parents = []
    parents_length = 0  # it includes all weight from opening and closing tags.
    fragment = ''
    events = soup._event_stream()
    state = Automata.pull
    PULL, PUSH, PUSH_DRAIN, PUSH_DRAIN_PUSH, CYCLE = range(5)
    track = PULL
    while state is not Automata.stop:
        if track == CYCLE:
            raise RuntimeError(f'{sourceline}:{sourcepos}: processing is in infinitive cycle.', sourceline, sourcepos)

        if __debug__:
            print(f'{budget=}/{max_len=} {state=!s} {fragment=} {event=!s} {parents_length=} {element_name=} {weight=} {piece=}')

        match state:
            case Automata.pull:
                pair = next(events, None)
                if pair is None:
                    state = Automata.stop

                else:
                    track = PULL
                    state = Automata.push

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

            case Automata.push:
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
                        if weight + budget > max_len:
                            state = Automata.drain

                        else:
                            state = Automata.pull
                            budget += weight
                            forward.append(piece)
                            elements.append(element)
                            backward.append(piece_end)
                            if atomic_index == len(parents) and element.name in split_tags:
                                atomic_index += 1
                            parents.append((element, weight))
                            parents_length += weight

                    case Event.END_ELEMENT_EVENT:
                        state = Automata.pull
                        forward.append(backward.pop())
                        elements.append(None)
                        piece = ''
                        _, weight = parents.pop()
                        parents_length -= weight
                        if len(parents) < atomic_index:
                            atomic_index -= 1

                    case Event.EMPTY_ELEMENT_EVENT | Event.STRING_ELEMENT_EVENT:
                        piece = element.output_ready(formatter=None)
                        weight = len(piece)
                        if weight + budget > max_len:
                            state = Automata.drain

                        else:
                            state = Automata.pull
                            budget += weight
                            forward.append(piece)
                            elements.append(None)

                    case unhandled:
                        raise RuntimeError(f'{sourceline}:{sourcepos}: unhandled event {unhandled!r}.', sourceline, sourcepos, unhandled)

            case Automata.drain:
                track += 1
                if parents_length + weight > max_len:
                    parents_tags = list(map(attrgetter("name"), map(itemgetter(0), parents)))
                    raise UnprocessedValue(
                        f'{sourceline}:{sourcepos}: piece {piece[:38]!r} and html around {"/".join(parents_tags)} cannot fit max_len ({max_len}).',
                        sourceline, sourcepos, piece, parents_tags, max_len
                    )

                state = Automata.push

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
                    budget += weight
                    forward.append(parent_piece)
                    elements.append(parent)

                budget += sum(map(len, leading_pieces))
                forward.extend(leading_pieces)
                elements.extend(leading_elements)

                print('')

    fragment = ''.join(forward+backward)
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
