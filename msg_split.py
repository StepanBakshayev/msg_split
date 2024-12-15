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
from typing import Iterator, Type

from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = frozenset("p b strong i ul ol div span".split(' '))  # ? | {BeautifulSoup.ROOT_TAG_NAME}


def measure(node: Type[PageElement], eventual_encoding, formatter) -> int:
    """
    Utility to get length of node.
    """
    if isinstance(node, Tag) and not node.is_empty_element:
        piece = node._format_tag(
            eventual_encoding, formatter, opening=True
        )
        piece_end = node._format_tag(
            eventual_encoding, formatter, opening=False
        )
        return len(piece) + len(piece_end)
    else:
        piece = node.output_ready(formatter=None)
        return len(piece)


def walk(source_node: Type[Tag], fragment_tree: PageElement, consumed: int, max_len: int, eventual_encoding, formatter) -> Iterator[Tag]:
    """
    Simple and recursive to be understandable by junior developer... by all time complexity consts.

    Fill fragment_tree from source_node until max_length. Yield each time max_length is exceeded.
    """
    # Measure current budget of the node.
    budget = measure(source_node, eventual_encoding, formatter)

    # Make sure there is a space to put the node. Otherwise, drain.
    if budget + consumed > max_len:
        # prepare fragment_tree to output.
        yield fragment_tree

        # build new tree.

    # copy node from source to destination

    # continue with children
    for child in source_node.content:
        # delegate draining
        yield from walk(child, fragment_tree, consumed, max_len, eventual_encoding, formatter)


def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:
    """Splits the original message (`source`) into fragments of the specified length
    (`max_len`)."""
    if max_len <= 1:
        raise ValueError(f'max_len argument ({max_len!r}) must be more then 0.', max_len)

    # shortcut
    if len(source) <= max_len:
        yield source
        return

    try:
        soup = BeautifulSoup(source, 'html.parser')
    except Exception as e:
        sourceline = None
        sourcepos = None
        raise UnprocessedValue(f'{sourceline}:{sourcepos}: source cannot be parsed.', sourceline, sourcepos) from e

    eventual_encoding = 'utf-8'
    formatter = soup.formatter_for_name('minimal')
    tree = BeautifulSoup()
    for fragment in walk(soup, tree, 0, max_len, eventual_encoding, formatter):
        yield fragment.decode()

    if tree.contents:
        yield tree.decode()


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
