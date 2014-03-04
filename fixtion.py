from functools import wraps
import sys
import inspect

from contextlib_extras import ExitStack


__all__ = ['fixture']


DEFAULT = object()


class _Fixture(object):
    def __init__(self, genfunc):
        self.genfunc = genfunc
        self.gen = None
        self.args = ()
        self.kwargs = {}
        self.patchings = getattr(genfunc, 'patchings', [])
        genfunc.patchings = []
        self.stack = ExitStack()

    def __call__(self, *args, **kw):
        # Just a single func arg was passed in. Decorate that func.
        if len(args) == 1 and len(kw) == 0 and inspect.isfunction(args[0]):
            return self.decorate_callable(args[0])

        # Not decorating yet. Just getting the args for the fixture function
        # (self.gen)
        self.args = args
        self.kwargs = kw

        return self

    def decorate_callable(self, func):
        if hasattr(func, 'fixtures'):
            func.fixtures.append(self)
            return func

        @wraps(func)
        def fixtured(*args, **keywargs):
            # don't use a with here (backwards compatability with Python 2.4)
            extra_args = []
            entered_fixtures = []

            # can't use try...except...finally because of Python 2.4
            # compatibility
            exc_info = tuple()
            fixture = None
            try:
                try:
                    for fixture in fixtured.fixtures:
                        arg = fixture.__enter__()
                        entered_fixtures.append(fixture)
                        if arg is not DEFAULT:
                            extra_args.append(arg)

                    args += tuple(extra_args)
                    return func(*args, **keywargs)
                except:
                    if fixture and fixture not in entered_fixtures:
                        # the fixture may have been started, but an exception
                        # raised whilst entering one of its additional_fixtures
                        entered_fixtures.append(fixture)
                    # Pass the exception to __exit__
                    exc_info = sys.exc_info()
                    # re-raise the exception
                    raise
            finally:
                for fixture in reversed(entered_fixtures):
                    fixture.__exit__(*exc_info)

        fixtured.fixtures = [self]

        return fixtured

    def __enter__(self):
        patchings = reversed(self.patchings)
        patchers = tuple(self.stack.enter_context(patching)
                         for patching in patchings)
        self.gen = self.genfunc(*(patchers + self.args), **self.kwargs)
        context = next(self.gen, None)
        if context is None:
            return DEFAULT
        return context

    def __exit__(self, *exc_info):
        try:
            next(self.gen, None)
        finally:
            self.stack.close()


def fixture(func):
    """Return a fixture decorator that acts as a function decorator or a context
    manager.

    `fixture` usage is similar to contextlib.contextmanager and behaves much
    like mock's patch function.

    The function being decorated must return a generator-iterator when called.
    This iterator must yield exactly one value, which will be bound to the
    targets in the with statement's as clause, if any.

    A typical usage that defines a basic fixture function:

        >>> from fixtion import fixture

        >>> @fixture
        ... def foo_fixture():
        ...   # The setup of the fixture
        ...   print 'enter foo fixture'
        ...   yield
        ...   # The teardown of the fixture
        ...   print 'exit foo fixture'

        >>> @foo_fixture
        ... def test_foo():
        ...   print 'foo'

        >>> test_foo()
        enter foo fixture
        foo
        exit foo fixture

    Decorating a test function with the fixture function will wrap the setup
    and teardown code (the stuff before and after the yield) around the test
    function invocation.

    An argument can also be passed in to the fixture function. If the fixture
    function yields a value then using it as a decorator will pass the value in
    as an extra argument to the decorated function. Used as context manager,
    the value is returned by the context manager.

        >>> @fixture
        ... def foo_fixture(a):
        ...     print 'enter foo_fixture(%r)' % a
        ...     class Context(object):
        ...         pass
        ...     context = Context()
        ...     yield context
        ...     print 'exit foo_fixture(%r)' % a

        >>> @foo_fixture(123)
        ... def test_foo(context):
        ...     print 'foo %r' % context

        >>> test_foo()
        enter foo_fixture(123)
        foo <fixtion.Context object at ...>
        exit foo_fixture(123)

    Also, works with mock's patch.

        >>> import random
        >>> from mock import patch
        >>>
        >>> @fixture
        ... @patch('random.randint', return_value=123)
        ... def patched_fixture(randint):
        ...   yield

        >>> @patched_fixture
        ... def test_patched():
        ...     print ('A random number '
        ...            'between 1 and 10: %r' % random.randint(1, 10))
        ...     print 'courtesy of %r' % random.randint

        >>> test_patched()
        A random number between 1 and 10: 123
        courtesy of <MagicMock name='randint' ...>

        >>> random.randint
        <bound method Random.randint of <random.Random object at ...>>

    """
    return _Fixture(func)
