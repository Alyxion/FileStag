"""
Helpful functions for working with iterators.
"""

from typing import Iterator, TypeVar

T = TypeVar("T")


def limit_iter(iterator: Iterator[T], count: int = -1) -> Iterator[T]:
    """
    Limit number of iterated elements from an iterable.

    :param iterator: The iterable
    :param count: The maximum count. -1 = unlimited
    """
    while count != 0:
        try:
            yield next(iterator)
        except StopIteration:
            return
        count -= 1


def batch_iter(iterator: Iterator[T], n: int, fast: bool = False) -> Iterator[list[T]]:
    """
    Creates an iterator which returns elements in batches of size n from
    an iterator.

    :param iterator: The iterator
    :param n: The count of elements per batch
    :param fast: If defined the whole iterator will be unwrapped into a list
        in "one go" which is usually like 3x-4x faster than iterative.
    :return: The next batch.

        Always a list of size n except for the last batch will contain the
        remaining elements.
    """
    if fast or isinstance(iterator, list):
        lst = list(iterator)
        for i in range(0, len(lst), n):
            yield lst[i : i + n]
    else:
        cur_list: list[T] = []
        for element in iterator:
            cur_list.append(element)
            if len(cur_list) == n:
                yield cur_list
                cur_list = []
        if len(cur_list):
            yield cur_list
