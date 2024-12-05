from argparse import ArgumentParser
from operator import itemgetter
from typing import Iterator

from bs4 import BeautifulSoup
from bs4.element import Tag

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = frozenset("p b strong i ul ol div span".split(' ')) | {BeautifulSoup.ROOT_TAG_NAME}


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""

    if max_len <= 1:
        raise ValueError(f'max_len argument ({max_len!r}) must be more then 0.', max_len)

    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        raise UnprocessedValue('source cannot be parsed.') from e

    eventual_encoding = 'utf-8'
    formatter = soup.formatter_for_name('minimal')

    budget = 0
    parents = []
    parents_weight = 0
    pieces = []
    elements = []
    weights = []
    for event, element in soup._event_stream():
        match event:
            case Tag.START_ELEMENT_EVENT:
                piece = element._format_tag(
                    eventual_encoding, formatter, opening=True
                )
                piece_end = element._format_tag(
                    eventual_encoding, formatter, opening=False
                )

                weight = len(piece) + len(piece_end)
                weights.append(weight + parents_weight)
                budget += weights[-1]
                parents_weight += weights[-1]
                elements.append((Tag.START_ELEMENT_EVENT, element))

                parents.append((element, piece, piece_end))

            case Tag.END_ELEMENT_EVENT:
                _, piece_start, piece = parents.pop()

                weight = -(len(piece_start))

            case Tag.EMPTY_ELEMENT_EVENT | Tag.STRING_ELEMENT_EVENT:
                piece = element.output_ready(formatter)
                # is parents variable always something?
                parent = parents[-1] if parents else None
                elements.append(parent)

            case unhandled:
                raise RuntimeError(f'unhandled event {unhandled!r}', unhandled)

        pieces.append(piece)

        if budget > max_len:
            # The loop makes at least one iteration because append operation is just above.
            for i, weight in enumerate(reversed(pieces), len(pieces)-1):
                budget -= weight
                if (budget <= max_len
                    and elements[i]
                    and elements[i][0].name in split_tags
                    and elements[i][1] is not Tag.START_ELEMENT_EVENT
                ):
                    break

            if i == 0:
                fragment = ''.join(pieces)
                raise UnprocessedValue(f'fragment {fragment[:38]=} cannot fit max_len ({max_len}).', fragment, max_len)

            dump = pieces[:i]
            pieces = pieces[i:]

            branch = elements[i-1][0]
            if elements[i-1][1] is Tag.END_ELEMENT_EVENT:
                branch = branch.parent

            closing = []
            while branch is not None:
                closing.append(branch._format_tag(
                    eventual_encoding, formatter, opening=False
                ))
                branch = branch.parent

            dump.extend(reversed(closing))

            fragment = ''.join(dump)
            assert len(fragment) == max_len, ('Fragment does not exceed limit.', fragment, len(fragment), max_len)

            yield fragment

    if pieces:
        dump = pieces
        i = len(pieces) -1
        branch = elements[i-1][0]
        if elements[i-1][1] is Tag.END_ELEMENT_EVENT:
            branch = branch.parent

        closing = []
        while branch is not None:
            closing.append(branch._format_tag(
                eventual_encoding, formatter, opening=False
            ))
            branch = branch.parent

        dump.extend(reversed(closing))

        fragment = ''.join(dump)
        assert len(fragment) == max_len, ('Fragment does not exceed limit.', fragment, len(fragment), max_len)

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
