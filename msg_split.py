"""
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

Author Stepan Bakshaev, 2024.
Contact stepan.bakshaev@keemail.me
"""
from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from operator import attrgetter, itemgetter
from typing import Iterator, Type

from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement, NavigableString

MAX_LEN = 4096


class UnprocessedValue(Exception):
    pass


split_tags = frozenset("p b strong i ul ol div span".split(' ')) | {BeautifulSoup.ROOT_TAG_NAME}


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
        piece = node.output_ready(formatter=formatter)
        return len(piece)


@dataclass
class Environment:
    """
    yield grabs return value. Use mutable object as data exchange in between recursive calls.
    """
    consumed: int  # overall length of fragment
    max_len: int  # limit for length
    forward: list[str]  # leading text chunks of fragment
    # forward_prefix_sum: list[int]
    backward: list[str] # closing tags, tail of text chunks of fragment
    # backward_prefix_sum: list[int]
    first_child: list[bool]  # it is used for cut parent-first_child from fragment.
    eventual_encoding: str  # BeautifulSoup
    formatter: str  # BeautifulSoup


def walk(source_node: PageElement, environment: Environment, first_child) -> Iterator[Tag]:
    """
    Simple and recursive to be understandable by junior developer... by all time complexity consts.
    """
    # Measure current budget of the node.
    # The trick is in a case of atomic node take all content. Hence, nothing to inspect on deeper level.
    forward = ''
    backward = ''
    # contents makes walk go deeper or not.
    contents = ()
    if isinstance(source_node, Tag):
        if source_node.name not in split_tags:
            forward = source_node.decode(formatter=environment.formatter)
        else:
            contents = source_node.contents
            forward = source_node._format_tag(
                environment.eventual_encoding, environment.formatter, opening=True
            )
            if not source_node.is_empty_element:
                backward = source_node._format_tag(
                    environment.eventual_encoding, environment.formatter, opening=False
                )
    else:
        assert isinstance(source_node, NavigableString), f'Unhandled type {type(source_node)}.'
        forward = source_node.output_ready(formatter=environment.formatter)

    length = len(forward) + len(backward)

    # Make sure there is a space to put the node. Otherwise, drain.
    if length + environment.consumed > environment.max_len:
        # First, calculate new consumption to figure out fitting into limit.
        # backward stays the same.
        consumed = sum(map(len, environment.backward))
        # forward is rebuilt by source_node parents.
        fresh_forward = []
        for node in source_node.parents:
            opening = node._format_tag(
                environment.eventual_encoding, environment.formatter, opening=True
            )
            consumed += len(opening)
            fresh_forward.append(opening)

        if length + consumed > environment.max_len:
            raise UnprocessedValue(
                f'{source_node.sourceline}:{source_node.sourcepos}: piece {forward[:38]!r}..{backward[:38]!r} and html around cannot fit max_len ({environment.max_len}).',
                source_node.sourceline, source_node.sourcepos, forward+backward, environment.max_len
            )

        forward_severed = len(environment.forward)
        backward_severed = len(environment.backward)
        # remove parent-first_child chain from fragment.
        if first_child:
            forward_severed -= 1
            backward_severed -= 1
            for marker in reversed(environment.first_child):
                if not marker:
                    break
                forward_severed -= 1
                backward_severed -= 1

        # make fragment
        yield ''.join(chain(environment.forward[:forward_severed], reversed(environment.backward[:backward_severed])))

        # fill forward and backward with source_node parents.




        if source_node.parent is not
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
