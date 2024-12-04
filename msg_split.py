from typing import Generator, Iterator
from bs4 import BeautifulSoup

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = "p b strong i ul ol div span".split(' ')


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""
    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        raise UnprocessedValue('source cannot be parsed.') from e

    print(f'{soup.prettify()=}')
    yield ''


if __name__ == '__main__':
    pass
