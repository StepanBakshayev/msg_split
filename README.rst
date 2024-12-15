============================
Split html message by chunks
============================

Task
====

Implement function `def split_message(source: str, max_len=MAX_LEN) -> Iterator[str]:` in file `msg_split.py`.
Message is html. There are tags allowed to split p, b, strong, i, ul, ol, div, span.
Output must be correct html.
Suggest to use BeautifulSoup.


Design (original)
=================

First attempt was a challenge to use stream events of parsed html. It provides O(N) time complexity and O(1) space complexity (limited b max_len).


Design (post mortem)
====================

It was revealed some facts after a review of original design.
Recursion is allowed. BeautifulSoup provides  <...> (some value, I vaguely remember tree and length from the review).

I want to try one more way to implement with uncovered tricks. I do not find any tips of length or ranges of strings from BeautifulSoup, but tree structure is for sure.
"Security through obscurity" never dies.
