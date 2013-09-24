from functools import wraps
import functools
import inspect
from itertools import chain

import mock

from contextdecorator import contextmanager, GeneratorContextManager, ContextDecorator
import sys
from contextlib_extras import ExitStack


_NO_EXCEPTION = (None, None, None)


def _reraise(cls, val, tb):
    raise cls, val, tb


class FixtureDecorator(object):
    "A base class or mixin that enables context managers to work as decorators."

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
    """Helper for @contextmanager decorator."""

    def __init__(self, func, gen, *args, **kwargs):
        self.func_gen = gen
        self.args = args
        self.kwargs = kwargs
        self.func = func
        self.stack = ExitStack()
#        if hasattr(self.func, '__test__'):
#        self.wrapper.__test__ = True
        # functools.update_wrapper(self.wrapper, func)

    def __get__(self, obj, type=None):
        if obj:
            return functools.partial(self.wrapper, obj)
        return self.wrapper

    def wrapper(self, obj=None):
        return self(obj)

    wrapper.__test__ = True

    def __call__(self, obj=None):
        context = self.__enter__()

#        obj = getattr(self.func, 'im_self', None)

        exc = _NO_EXCEPTION
        try:
            args = tuple(filter(None, (obj, context)))
            result = self.func(*args)
        except Exception:
            exc = sys.exc_info()
            result = None

        catch = self.__exit__(*exc)

        if not catch and exc is not _NO_EXCEPTION:
            _reraise(*exc)

        return result

    def __enter__(self):
    #        patchers = tuple(self.stack.enter_context(patch)
    #                         for patch in reversed(getattr(self.gen, 'patchings', [])))
    #        self.gen = self.gen(*chain(patchers, self.args), **self.kwargs)
        self.gen = self.func_gen(*self.args, **self.kwargs)

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
                return func()(*args, **kw) # create class before usage
            return func(*args, **kw)

        class_wrapper.__name__ = func.__name__
        class_wrapper.__module__ = func.__module__
        return class_wrapper

    @functools.wraps(func)
    def func_wrapper(*args, **kw):
        if isFuncArg(*args, **kw):
            return func(*args, **kw)

        def functor(userFunc):
            return func(userFunc, *args, **kw)

        return functor

    return func_wrapper


@decorator
def fixture(func):
#    @wraps(func)
    @decorator
    def wrapper(test_func, *args, **kwds):
        functools.update_wrapper(wrapper, test_func)
        return GeneratorFixtureManager(test_func, func, *args, **kwds)

    #    func.fixture_patchings, func.patchings = getattr(func, 'patchings', []), []
    return wrapper


def patch(target, new=mock.DEFAULT, spec=None, create=False,
          spec_set=None, autospec=None, new_callable=None, **kwargs):
    getter, attribute = mock._get_target(target)
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs)


class _patch(mock._patch):
    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            return patcher(func, patched.patchings, *args, **keywargs)

        patched.patchings = [self]
        if hasattr(func, 'func_code'):
            # not in Python 3
            patched.compat_co_firstlineno = getattr(
                func, "compat_co_firstlineno",
                func.func_code.co_firstlineno
            )
        return patched


#@contextmanager
def patcher(func, patchings, *args, **keywargs):
    # don't use a with here (backwards compatability with Python 2.4)
    extra_args = []
    entered_patchers = []

    def stop_patchers():
        for patching in reversed(entered_patchers):
            patching.__exit__(*exc_info)

    # can't use try...except...finally because of Python 2.4
    # compatibility
    exc_info = tuple()
    patching = None
    try:
        try:
            for patching in patchings:
                arg = patching.__enter__()
                entered_patchers.append(patching)
                if patching.attribute_name is not None:
                    keywargs.update(arg)
                elif patching.new is mock.DEFAULT:
                    extra_args.append(arg)

            args += tuple(extra_args)
            gen = func(*args, **keywargs)

        except:
            if (patching not in entered_patchers and
                mock._is_started(patching)):
                # the patcher may have been started, but an exception
                # raised whilst entering one of its additional_patchers
                entered_patchers.append(patching)
                # Pass the exception to __exit__
            exc_info = sys.exc_info()
            # re-raise the exception
            raise

    finally:
        stop_patchers()

    yield next(gen)

    next(gen)

    stop_patchers()

#@fixture
#@mock.patch('logging.error')
#def myfixture(a_mock):
#    print repr(a_mock)
#    print 'before'
#    yield
#    print 'after'
#
#
#@myfixture
#def test():
#    print 'tada'


@fixture
def basic_fixture():
    print 'before basic'
    yield
    print 'after basic'


@basic_fixture
def test_basic():
    print 'tada - test_basic'


@fixture
def a_fixture(a):
    print 'before a: %r' % a
    yield
    print 'after a: %r' % a


@a_fixture(42)
def test_with_a():
    print 'tada - test_with_a'


@fixture
def b_fixture():
    print 'before b'
    yield 42
    print 'after b'


@b_fixture
def test_with_b(context):
    print 'tada - test_with_b: %r' % context


import logging


@fixture
@patch('logging.error')
def c_fixture(logging_mock):
    print 'before c: %r' % logging.error
    yield
    print 'after c: %r' % logging.error


@c_fixture
def test_with_c():
    print 'tada - test_with_c'


@fixture
@patch('logging.info')
def example_fixture(logging_mock):
    print 'enter example_fixture: %r' % logging.error
    yield 123
    print 'exit example_fixture: %r' % logging.error


@example_fixture
def test_using_example_fixture(context):
    print '  tada - test_using_example_fixture'
    print '  context: %r' % context


if __name__ == '__main__':
    test_basic()
    test_with_a()
    test_with_b()
    test_with_c()
    test_using_example_fixture()