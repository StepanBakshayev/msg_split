from argparse import ArgumentParser
from typing import Iterator

from bs4 import BeautifulSoup
from bs4.element import Tag

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = frozenset("p b strong i ul ol div span".split(' '))


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    if max_len <= 1:
        raise ValueError(f'max_len argument ({max_len!r}) must be more then 0.', max_len)

    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""
    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        raise UnprocessedValue('source cannot be parsed.') from e

    eventual_encoding = 'utf-8'
    formatter = soup.formatter_for_name('minimal')

    budget = max_len
    parents = []
    run = []
    for event, element in soup._event_stream():
        match event:
            case Tag.START_ELEMENT_EVENT:
                piece = element._format_tag(
                    eventual_encoding, formatter, opening=True
                )
            case Tag.END_ELEMENT_EVENT:
                piece = element._format_tag(
                    eventual_encoding, formatter, opening=False
                )
            case Tag.EMPTY_ELEMENT_EVENT | Tag.STRING_ELEMENT_EVENT:
                piece = element.output_ready(formatter)
            case unhandled:
                raise RuntimeError(f'unhandled event {unhandled!r}', unhandled)

        piece_size = len(piece)

        if budget < piece_size:
            yield ''.join(run)
            run.clear()
            budget = max_len

        run.append(piece)
        budget -= piece_size

    if run:
        yield ''.join(run)


def main(opts):
    with open(opts.source, 'rt') as stream:
        source = stream.read()

    for number, chunk in enumerate(split_message(source, max_len=opts.max_len)):
        fragmen_length = len(chunk)
        print(f'fragment #{number}: {fragmen_length} chars.')
        print(chunk)


if __name__ == '__main__':
    arguments = ArgumentParser(description='Split html message by chunks in max-len size.')
    arguments.add_argument('--max-len', type=int, default=MAX_LEN)
    arguments.add_argument('source', help='Path to source file.')

    main(arguments.parse_args())
