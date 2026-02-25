import importlib
from functools import partial
from typing import Iterable, List, Type, Callable

from spherov2.toy import Toy
from spherov2.toy.bb8 import BB8
from spherov2.toy.bb9e import BB9E


class ToyNotFoundError(Exception):
    ...


def all_toys(cls=Toy):
    subtypes = cls.__subclasses__()
    yield cls
    for sub in subtypes:
        yield from all_toys(sub)


def find_toys(*, timeout=5.0, toy_types: Iterable[Type[Toy]] = None,
              toy_names: Iterable[str] = None, adapter=None) -> List[Toy]:
    """Find toys that matches the criteria given.

    :param timeout: Device scanning timeout, in seconds.
    :param toy_types: Iterable of toy types (subclasses of :class:`Toy`) that needs to be scanned. Set to ``None`` to scan
                      all toy types available.
    :param toy_names: Iterable of strings of toy names that needs to be scanned. Set to ``None`` to scan toys with all
                      kinds of names.
    :param adapter: Kind of adapter to use for scanning bluetooth devices. Set to ``None`` to use default
                    :class:`BleakAdapter`.
    :return: A list of toys that are scanned.
    """
    if adapter is None:
        adapter = importlib.import_module(
            'spherov2.adapter.bleak_adapter').BleakAdapter
    if toy_names is not None:
        toy_names = set(toy_names)
    if toy_names is not None and len(toy_names) == 1:
        toy = adapter.scan_toy(list(toy_names)[0], timeout)
        if toy is None:
            return []
        toys = [toy]
    else:
        toys = adapter.scan_toys(timeout)
    if toy_types is None:
        toy_types = set(all_toys())
    ret = []
    for toy in toys:
        if toy.name is None:
            continue
        if toy_names is not None and toy.name not in toy_names:
            continue
        for toy_cls in toy_types:
            toy_type = toy_cls.toy_type
            if toy.name.startswith(toy_type.filter_prefix) and \
                    (toy_type.prefix is None or toy.name.startswith(toy_type.prefix)):
                ret.append(toy_cls(toy, adapter))
                break
    return ret


def find_toy(*, toy_name: str = None, **kwargs) -> Toy:
    """Find a single toy that matches the criteria given.

    :param toy_name: A string of toy name that needs to be scanned. Set to ``None`` to scan toy with all kinds of names.
    :param timeout: Device scanning timeout, in seconds.
    :param toy_types: List of toy types (subclasses of :class:`Toy`) that needs to be scanned. Set to ``None`` to scan
                      all toy types available.
    :param adapter: Kind of adapter to use for scanning bluetooth devices. Set to ``None`` to use default
                    :class:`BleakAdapter`.
    :return: A toy that is scanned.
    :raise ToyNotFoundError: If no toys could be found
    """
    toys = find_toys(toy_names=[toy_name] if toy_name else None, **kwargs)
    if not toys:
        raise ToyNotFoundError
    return toys[0]


find_BB8: Callable[..., BB8] = partial(find_toy, toy_types=[BB8])
find_BB9E: Callable[..., BB9E] = partial(find_toy, toy_types=[BB9E])
