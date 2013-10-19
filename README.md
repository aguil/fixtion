Examples
--------

A basic fixture function definition:

    >>> from fixtion import fixture
    >>>
    >>> @fixture
    ... def basic_fixture():
    ...   print 'enter basic fixture'
    ...   yield
    ...   print 'exit basic fixture'

Decorating a test function with the basic fixture function will wrap the setup
and teardown code (the stuff before and after the yield) around the test
function invocation:

    >>> @basic_fixture
    ... def test_basic():
    ...   print '-- A test setup with a basic fixture'
    >>>
    >>> test_basic()
    enter basic fixture
    -- A test setup with a basic fixture
    exit basic fixture


Decorating unittest.TestCase test methods work, too:

    >>> import unittest
    >>>
    >>> class Tester(unittest.TestCase):
    ...   @basic_fixture
    ...   def test_foo(self):
    ...     print '-- a standard unittest fixtured using fixtion'
    >>>
    >>> tester = Tester('test_foo')
    >>> tester.test_foo()
    enter basic fixture
    -- a standard unittest fixtured using fixtion
    exit basic fixture


Change and restore os.environ:

    >>> import os
    >>>
    >>> @fixture
    ... def environ_fixture(**kwargs):
    ...   # Save the original environment values then update the environ.
    ...   original = {k: v for k, v in os.environ.iteritems() if k in kwargs}
    ...   os.environ.update(**kwargs)
    ...
    ...   yield
    ...
    ...   # Restore the original environment values.
    ...   for key in kwargs:
    ...     os.environ.pop(key)
    ...   os.environ.update(**original)
    >>>
    >>> @environ_fixture(foo='bar')
    ... def test_environ():
    ...   print 'foo: %r' % os.environ['foo']
    >>>
    >>> test_environ()
    foo: 'bar'
    >>>
    >>> 'foo' in os.environ
    False


Return some test context:

    >>> @fixture
    ... def login_fixture():
    ...   class context(object):
    ...     username = 'ksoze'
    ...
    ...   yield context()
    >>>
    >>> @login_fixture
    ... def test_login(context):
    ...   print context.username
    >>>
    >>> test_login()
    ksoze


Works with mock.patch:

    >>> import random
    >>> import mock
    >>>
    >>> @fixture
    ... @mock.patch('random.randint', return_value=123)
    ... def patched_fixture(randint):
    ...   yield
    >>>
    >>> @patched_fixture
    ... def test_patched():
    ...     print 'A random number between 1 and 10: %r' % random.randint(1, 10)
    ...     print 'courtesy of %r' % random.randint
    >>>
    >>> test_patched()
    A random number between 1 and 10: 123
    courtesy of <MagicMock name='randint' ...>
    >>>
    >>> random.randint
    <bound method Random.randint of <random.Random object at ...>>


The previous os.environ example can be really simplified:

  >>> @fixture
  ... def environ_fixture(**kwargs):
  ...   with mock.patch.dict('os.environ', kwargs):
  ...     yield
  >>>
  >>> @environ_fixture(foo='bar')
  ... def test_environ():
  ...   print 'foo: %r' % os.environ['foo']
  >>>
  >>> test_environ()
  foo: 'bar'
  >>>
  >>> 'foo' in os.environ
  False


