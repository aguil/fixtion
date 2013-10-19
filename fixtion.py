import functools
from functools import wraps
import sys
import inspect
from itertools import chain

from contextlib_extras import ExitStack


_NO_EXCEPTION = (None, None, None)


def _reraise(cls, val, tb):
    raise cls, val, tb


class FixtureDecorator(object):
    """A base class or mixin that enables fixture function context managers to
        work as decorators.
    """
    def __call__(self, f):
        @wraps(f)
        def inner(*args, **kw):
            self.__enter__()

            exc = _NO_EXCEPTION
            try:
                result = f(*args, **kw)
            except Exception:
                exc = sys.exc_info()

            catch = self.__exit__(*exc)

            if not catch and exc is not _NO_EXCEPTION:
                _reraise(*exc)
            return result

        return inner


class GeneratorFixtureManager(FixtureDecorator):
    """Helper for @fixture decorator."""
    def __init__(self, func, gen, *args, **kwargs):
        self.func_gen = gen
        self.args = args
        self.kwargs = kwargs
        self.func = func
        self.stack = ExitStack()

    def __get__(self, obj, type=None):
        if obj:
            return functools.partial(self.wrapper, obj)
        return self.wrapper

    def wrapper(self, obj=None):
        return self(obj)

    wrapper.__test__ = True

    def __call__(self, obj=None):
        context = self.__enter__()

        exc = _NO_EXCEPTION
        result = None
        try:
            args = tuple(filter(None, (obj, context)))
            result = (self.func
                        and self.func(*args)
                        or None)
        except Exception:
            exc = sys.exc_info()

        catch = self.__exit__(*exc)

        if not catch and exc is not _NO_EXCEPTION:
            _reraise(*exc)

        return result

    def __enter__(self):
        fixture_patchings = reversed(
            getattr(self.func_gen, 'fixture_patchings', []))

        patchers = tuple(
            self.stack.enter_context(patch) for patch in fixture_patchings)

        self.gen = self.func_gen(*chain(patchers, self.args), **self.kwargs)

        try:
            context = next(self.gen)
            return context

        except StopIteration:
            raise RuntimeError("generator didn't yield")

    def __exit__(self, type, value, traceback):
        try:
            if type is None:
                try:
                    next(self.gen)
                except StopIteration:
                    return
                else:
                    raise RuntimeError("generator didn't stop")
            else:
                if value is None:
                    # Need to force instantiation so we can reliably
                    # tell if we get the same exception back
                    value = type()
                try:
                    self.gen.throw(type, value, traceback)
                    raise RuntimeError("generator didn't stop after throw()")
                except StopIteration:
                    # Suppress the exception *unless* it's the same exception that
                    # was passed to throw().  This prevents a StopIteration
                    # raised inside the "with" statement from being suppressed
                    exc = sys.exc_info()[1]
                    return exc is not value
                except:
                    # only re-raise if it's *not* the exception that was
                    # passed to throw(), because __exit__() must not raise
                    # an exception unless __exit__() itself failed.  But throw()
                    # has to raise the exception to signal propagation, so this
                    # fixes the impedance mismatch between the throw() protocol
                    # and the __exit__() protocol.
                    #
                    if sys.exc_info()[1] is not value:
                        raise
        finally:
            self.stack.close()


def decorator(func):
    ''' Allow to use decorator either with arguments or not. '''

    def isFuncArg(*args, **kw):
        return len(args) == 1 and len(kw) == 0 and (
            inspect.isfunction(args[0]) or isinstance(args[0], type))

    if isinstance(func, type):
        def class_wrapper(*args, **kw):
            if isFuncArg(*args, **kw):
                inst = func()
                return inst(*args, **kw) # create class before usage
            return func(*args, **kw)

        class_wrapper.__name__ = func.__name__
        class_wrapper.__module__ = func.__module__
        return class_wrapper

    @functools.wraps(func)
    def func_wrapper(*args, **kw):
        if isFuncArg(*args, **kw):
            return func(*args, **kw)

        def functor(userFunc=None):
            return func(userFunc, *args, **kw)

        return functor

    return func_wrapper


@decorator
def fixture(func):
    @wraps(func)
    @decorator
    def wrapper(test_func, *args, **kwds):
        if test_func:
            functools.update_wrapper(wrapper, test_func)
        return GeneratorFixtureManager(test_func, func, *args, **kwds)

    func.fixture_patchings, func.patchings = getattr(func, 'patchings', []), []
    return wrapper
