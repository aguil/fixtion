from types import FunctionType
import unittest

import mock

from fixtion import fixture, basic_fixture


something = mock.sentinel.Something
something_else = mock.sentinel.SomethingElse


class Foo(object):
    pass


def bar():
    pass


#class FixtureContextDecorator_tests(unittest.TestCase):
#    def test_returns_no_context(self):
#        class myfixture(FixtureContextDecorator):
#            def __enter__(self):
#                pass
#
#            def __exit__(self, *exc):
#                pass
#
#        myfixture = myfixture()
#
#        @myfixture
#        def test(context):
#            self.assertEqual(None, context)
#
#        test()
#
#    def test_returns_context(self):
#        class myfixture(FixtureContextDecorator):
#            def __enter__(self):
#                return 42
#
#            def __exit__(self, *exc):
#                pass
#
#        myfixture = myfixture()
#
#        @myfixture
#        def test(context):
#            self.assertEqual(42, context)
#
#        test()
#
#    def test_returns_self(self):
#        class myfixture(FixtureContextDecorator):
#            def __enter__(self):
#                return self
#
#            def __exit__(self, *exc):
#                pass
#
#        myfixture = myfixture()
#
#        @myfixture
#        def test(context):
#            self.assertIs(myfixture, context)
#
#        test()
#
#    def test_with_mock(self):
#        class myfixture(FixtureContextDecorator):
#            def __enter__(self):
#                return self
#
#            def __exit__(self, *exc):
#                pass
#
#        myfixture = myfixture()
#
#        @mock.patch('%s.bar' % __name__)
#        @mock.patch('%s.Foo' % __name__)
#        @myfixture
#        def test(foo_mock, bar_mock, context):
#            self.assertIsInstance(foo_mock, mock.Mock)
#            self.assertEqual('Foo', foo_mock._mock_name)
#
#            self.assertIsInstance(bar_mock, mock.Mock)
#            self.assertEqual('bar', bar_mock._mock_name)
#
#            self.assertIs(myfixture, context)
#
#        test()


@fixture
def basic_fixture():
    yield


@fixture
@mock.patch('random.randint', return_value=123)
def patched_fixture(randint):
    class context(object):
        randint_stub = randint
    yield context()


mock_function = mock.MagicMock(spec=FunctionType, __test__=False)
mock_fixture = fixture(mock_function)


class basic_fixture_tester(unittest.TestCase):
    @mock_fixture
    def test_basic_fixture(self):
        mock_function.assert_called_once()


class patched_fixture_tester(unittest.TestCase):
    @patched_fixture
    def test_patched_fixture(self, context):
        self.assertTrue(False)
        self.assertIsInstance(context.randint_stub, unittest.TestCase)

#class fixture_function_tests(unittest.TestCase):
#    def test_basic(self):
#        @fixture
#        def some_fixture():
#            class context(object):
#                foo = 42
#            yield context
#
#        @some_fixture
#        def test(context):
#            self.assertEqual(42, context.foo)
#
#        test()
#
#    def test_with_arg(self):
#        @fixture
#        def some_fixture(a):
#            yield a
#
#        @some_fixture(params=(42,))
#        def test(context):
#            self.assertEqual(42, context)
#
#        test()
#
#    def test_with_mock(self):
#        Foo_original = Foo
#
#        @fixture(patchings=(mock.patch('%s.Foo' % __name__),))
#        def some_fixture(foo_mock):
#            self.assertIsInstance(foo_mock, mock.Mock)
#            self.assertEqual('Foo', foo_mock._mock_name)
#
#            class context(object):
#                foo = 42
#
#            yield context
#
#            self.assertIsInstance(foo_mock, mock.Mock)
#            self.assertEqual('Foo', foo_mock._mock_name)
#
#        @some_fixture
#        def test(context):
#            self.assertEqual(42, context.foo)
#            self.assertIsInstance(Foo, mock.Mock)
#
#        test()
#        self.assertIs(Foo, Foo_original)
#
#    def test_with_arg_and_mock(self):
#        Foo_original = Foo
#
##        @fixture(patchings=(mock.patch('%s.Foo' % __name__),))
#        @mock.patch('%s.Foo' % __name__)
#        @fixture
#        def some_fixture(a, foo_mock):
#            self.assertIsInstance(foo_mock, mock.Mock)
#            self.assertEqual('Foo', foo_mock._mock_name)
#
#            class context(object):
#                foo = 42
#
#            yield context
#
#            self.assertIsInstance(foo_mock, mock.Mock)
#            self.assertEqual('Foo', foo_mock._mock_name)
#
#        @some_fixture(params=(42,))
#        def test(context):
#            self.assertEqual(42, context.foo)
#            self.assertIsInstance(Foo, mock.Mock)
#
#        test()
#        self.assertIs(Foo, Foo_original)
