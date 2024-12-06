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
    opening = False
    backward = []
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
                            opening = True
                            backward.append(piece_end)
                            parents.append((element, weight))
                            parents_length += weight

                    case Event.END_ELEMENT_EVENT:
                        state = Automata.pull
                        forward.append(backward.pop())
                        opening = False
                        piece = ''
                        _, weight = parents.pop()
                        parents_length -= weight

                    case Event.EMPTY_ELEMENT_EVENT | Event.STRING_ELEMENT_EVENT:
                        piece = element.output_ready(formatter=None)
                        weight = len(piece)
                        if weight + budget > max_len:
                            state = Automata.drain

                        else:
                            state = Automata.pull
                            budget += weight
                            forward.append(piece)
                            opening = False

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

                if opening:
                    fragment = ''.join(forward[:-len(backward)])
                    forward = forward[-len(backward):]
                else:
                    fragment = ''.join(chain(forward, reversed(backward)))
                    forward.clear()
                    for parent, _ in parents:
                        parent_piece = parent._format_tag(
                            eventual_encoding, formatter, opening=True
                        )
                        forward.append(parent_piece)

                assert len(fragment) <= max_len, ('Fragment length fits max_len', sourceline, sourcepos, fragment[:38], len(fragment), max_len)
                yield fragment

                budget = parents_length

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
