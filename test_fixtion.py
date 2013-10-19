import unittest
from unittest import skip

import mock

from fixtion import fixture


class Foo(object):
    pass


@fixture
def basic_fixture():
    class Context(object):
        def __init__(self):
            self.enter = mock.Mock()
            self.exit = mock.Mock()
    context = Context()
    context.enter()
    yield context
    context.exit()


@fixture
@mock.patch('random.randint', return_value=123)
def patched_fixture(randint):
    class context(object):
        randint_stub = randint
    yield context()


@fixture
def patched_dict_fixture(**kwargs):
    with mock.patch.dict('os.environ', kwargs):
        yield


@fixture
@mock.patch.dict('os.environ', foo='bar')
def patched_dict_decorated_fixture():
    yield


class basic_fixture_tester(unittest.TestCase):
    @basic_fixture
    def test_fixture_entered(self, context):
        context.enter.assert_called_once_with()

    def test_fixture_entered(self):
        @basic_fixture
        def foo(context):
            return context
        foo().enter.assert_called_once_with()

    def test_foo_fixture_as_context_manager(self):
        # TODO: Rid this ()() ugliness.
        with basic_fixture()():
            pass


class patched_fixture_tester(unittest.TestCase):
    @patched_fixture
    def test_patched_fixture(self, context):
        self.assertIsInstance(context.randint_stub, mock.MagicMock)


class patched_dict_fixture_tests(unittest.TestCase):
    @patched_dict_fixture(foo='bar')
    def test_has_foo_value(self):
        import os
        self.assertEqual('bar', os.environ['foo'])

    def test_removes_foo_value(self):
        import os
        with patched_dict_fixture(foo='bar')():
            pass
        self.assertNotIn('foo', os.environ)

    @mock.patch.dict('os.environ', {'foo': 'buzz'})
    def test_changes_foo_value(self):
        import os
        with patched_dict_fixture(foo='bar')():
            self.assertEqual('bar', os.environ['foo'])

    @mock.patch.dict('os.environ', {'foo': 'buzz'})
    def test_restores_foo_value(self):
        import os
        with patched_dict_fixture(foo='bar')():
            pass
        self.assertEqual('buzz', os.environ['foo'])


@skip('TODO: Make @patch.dict work')
class patched_dict_decorated_fixture_tests(unittest.TestCase):
    @patched_dict_decorated_fixture
    def test_has_foo_value(self):
        import os
        self.assertIn('foo', os.environ)
        self.assertEqual('bar', os.environ['foo'])

    @patched_dict_decorated_fixture
    def test_removes_foo_value(self):
        import os
        with patched_dict_fixture(foo='bar')():
            pass
        self.assertNotIn('foo', os.environ)

    @mock.patch.dict('os.environ', {'foo': 'buzz'})
    def test_changes_foo_value(self):
        import os

        actual = {}

        @patched_dict_decorated_fixture
        def test():
            actual['foo'] = os.environ['foo']

        test()
        self.assertEqual({'foo': 'bar'}, actual)

    @mock.patch.dict('os.environ', {'foo': 'buzz'})
    def test_restores_foo_value(self):
        import os

        @patched_dict_decorated_fixture
        def test():
            pass

        test()
        self.assertEqual('buzz', os.environ['foo'])


class fixture_function_tests(unittest.TestCase):
    def test_basic(self):
        @fixture
        def some_fixture():
            class context(object):
                foo = 123

            yield context

        @some_fixture
        def test(context):
            self.assertEqual(123, context.foo)

        test()

    def test_with_arg(self):
        @fixture
        def some_fixture(a):
            yield a

        @some_fixture(123)
        def test(context):
            self.assertEqual(123, context)

        test()

    def test_with_mock_patch(self):
        Foo_original = Foo

        @fixture
        @mock.patch('test_fixtion.Foo')
        def some_fixture(foo_mock):
            self.assertIsInstance(foo_mock, mock.Mock)
            self.assertEqual('Foo', foo_mock._mock_name)

            class context(object):
                foo = 123

            yield context

            self.assertIsInstance(foo_mock, mock.Mock)
            self.assertEqual('Foo', foo_mock._mock_name)

        @some_fixture
        def test(context):
            self.assertEqual(123, context.foo)
            self.assertIsInstance(Foo, mock.Mock)

        test()
        self.assertIs(Foo, Foo_original)

    def test_with_arg_and_mock(self):
        Foo_original = Foo

        @fixture
        @mock.patch('test_fixtion.Foo')
        def some_fixture(foo_mock, a):
            self.assertIsInstance(foo_mock, mock.Mock)
            self.assertEqual('Foo', foo_mock._mock_name)

            class context(object):
                foo = a

            yield context

            self.assertIsInstance(foo_mock, mock.Mock)
            self.assertEqual('Foo', foo_mock._mock_name)

        @some_fixture(123)
        def test(context):
            self.assertEqual(123, context.foo)
            self.assertIsInstance(Foo, mock.Mock)

        test()
        self.assertIs(Foo, Foo_original)

    @skip('TODO: Compose fixtures')
    def test_compose_fixtures(self):
        from mock import call

        context = mock.Mock()

        @fixture
        def foo_fixture():
            context.enter_foo()
            yield
            context.exit_foo()

        @foo_fixture
        def foobar_fixture():
            context.enter_bar()
            yield
            context.exit_bar()

        @foobar_fixture
        def test():
            pass

        test()

        self.assertEqual(
            [call.enter_foo(), call.enter_bar(), call.exit_bar(),
             call.exit_foo()],
            context.mock_calls)

    @skip('TODO: Stack fixtures')
    def test_stack_fixtures(self):
        from mock import call

        context = mock.Mock()

        @fixture
        def foo_fixture():
            context.enter_foo()
            yield
            context.exit_foo()

        @fixture
        def bar_fixture():
            context.enter_bar()
            yield
            context.exit_bar()

        @foo_fixture
        @bar_fixture
        def test():
            pass

        test()

        self.assertEqual(
            [call.enter_foo(), call.enter_bar(), call.exit_bar(),
             call.exit_foo()],
            context.mock_calls)
