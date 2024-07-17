# ruff: noqa: ANN401, N801, D107, D105
"""Module of additional types."""

from collections.abc import Callable
from typing import Any, Generic, Optional, TypeVar, Union

from typing_extensions import Self

GetT = TypeVar('GetT')
SetT = TypeVar('SetT')


class typed_property(Generic[GetT, SetT]):
    """Typed property.

    For more information, see here: https://docs.python.org/3/howto/descriptor.html#properties

    It can be used as a workaround for typed properties with different types.
    This is a known problem https://github.com/python/mypy/issues/3004.

    Usage example:

    >>> class Test:
    >>>     def __init__(self) -> None:
    >>>         self._value = 1
    >>>     @TypedProperty[int, int | float]
    >>>     def value(self) -> int:
    >>>         return self._value
    >>>     @value.setter
    >>>     def set_value(self, val: int | float) -> None:
    >>>         self._value = int(val)
    >>>     @value.deleter
    >>>     def del_value(self) -> None:
    >>>         del self._value

    >>> t = Test()
    >>> assert t.value == 1
    >>> t.value = 2
    >>> assert t.value == 2
    >>> t.set_value(3)
    >>> assert t.value == 3
    >>> del t.value
    >>> try:
    >>>     t.value
    >>> except AttributeError:
    >>>     pass
    >>> else:
    >>>     raise Exception
    >>> t.value = 4
    >>>     assert t.value == 4
    """
    fget: Optional[Callable[[Any], GetT]]
    fset: Optional[Callable[[Any, SetT], None]]
    fdel: Optional[Callable[[Any], None]]

    def __init__(
        self,
        fget: Optional[Callable[[Any], GetT]] = None,
        fset: Optional[Callable[[Any, SetT], None]] = None,
        fdel: Optional[Callable[[Any], None]] = None,
        doc: Optional[str] = None,
    ) -> None:
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc
        self._name = ''

    def __set_name__(self, owner: Any, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: Any = None) -> Union[GetT, Self]:
        if obj is None:
            return self
        if self.fget is None:
            msg = f'property {self._name!r} has no getter'
            raise AttributeError(msg)
        return self.fget(obj)

    def __set__(self, obj: Any, value: SetT) -> None:
        if self.fset is None:
            msg = f'property {self._name!r} has no setter'
            raise AttributeError(msg)
        self.fset(obj, value)

    def __delete__(self, obj: Any) -> None:
        if self.fdel is None:
            msg = f'property {self._name!r} has no deleter'
            raise AttributeError(msg)
        self.fdel(obj)

    def getter(self, fget: Callable[[Any], GetT]) -> Callable[[Any], GetT]:
        """Decorator for getter."""
        self.fget = fget
        return fget

    def setter(self, fset: Callable[[Any, SetT], None]) -> Callable[[Any, SetT], None]:
        """Decorator for setter."""
        self.fset = fset
        return fset

    def deleter(self, fdel: Callable[[Any], None]) -> Callable[[Any], None]:
        """Decorator for deleter."""
        self.fdel = fdel
        return fdel
