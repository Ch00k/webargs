# -*- coding: utf-8 -*-
import mock

import pytest

from webargs.core import (
    Parser,
    Arg,
    ValidationError,
    Missing,
    get_value,
    PY2,
    text_type,
    long_type,
    NON_NULLABLE_TYPES,
    TYPES
)

from uuid import UUID

if not PY2:
    unicode = str


class MockRequestParser(Parser):
    """A minimal parser implementation that parses mock requests."""

    def parse_json(self, web_request, name, arg):
        return get_value(web_request.json, name, arg.multiple)


@pytest.fixture
def web_request():
    return mock.Mock()

@pytest.fixture
def parser():
    return MockRequestParser()


class TestArg:

    def test_bad_validate_param(self):
        with pytest.raises(ValueError):
            Arg(validate='bad')

    def test_validated(self):
        arg = Arg(validate=lambda x: x == 42)
        assert arg.validated('foo', 42) == 42
        with pytest.raises(ValidationError):
            arg.validated('foo', 32)

    def test_validated_with_nonascii_input(self):
        arg = Arg(validate=lambda t: False)
        text = u'øˆ∆´ƒº'
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', text)
        assert text in unicode(excinfo)

    def test_validated_with_conversion(self):
        arg = Arg(validate=lambda x: x == 42, type_=int)
        assert arg.validated('foo', '42') == 42

    def test_validated_with_bad_type(self):
        arg = Arg(type_=int)
        assert arg.validated('foo', 42) == 42
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', 'nonint')
        assert 'Expected type integer for foo, got string' in str(excinfo)

    @pytest.mark.parametrize('arg_type', NON_NULLABLE_TYPES)
    def test_validated_non_nullable_types(self, arg_type):
        print(arg_type)
        arg = Arg(type_=arg_type)
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', None)
        assert 'Expected type {0} for foo, got null'.format(TYPES[arg_type]) in str(excinfo)

    def test_validated_null(self):
        arg = Arg(type_=dict)
        assert arg.validated('foo', {}) == {}
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', None)
        assert 'Expected type object for foo, got null' in str(excinfo)

    def test_validated_null_noop(self):
        arg = Arg()
        assert arg.validated('foo', {}) == {}
        assert arg.validated('foo', None) is None

    def test_validated_text_type(self):
        arg = Arg(type_=text_type)
        assert arg.validated('foo', 42) == '42'

    def test_validated_long_type(self):
        arg = Arg(type_=long_type)
        assert arg.validated('foo', 42) == 42

    def test_validated_unknown_type(self):
        arg = Arg(type_=UUID)
        assert (arg.validated('foo', '12345678123456781234567812345678') ==
                UUID('12345678-1234-5678-1234-567812345678'))
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', None)
        assert 'Expected type UUID for foo, got null' in str(excinfo)

    def test_custom_error(self):
        arg = Arg(type_=int, error='not an int!')
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', 'badinput')
        assert 'not an int!' in str(excinfo)

    def test_default_valdation_msg(self):
        arg = Arg(validate=lambda x: x == 42)
        with pytest.raises(ValidationError) as excinfo:
            arg.validated('foo', 1)
        assert 'Validator <lambda>(1) is not True' in str(excinfo)

    def test_conversion_to_str(self):
        arg = Arg(str)
        assert arg.validated('foo', 42) == '42'

    def test_use_param(self):
        arg = Arg(use=lambda x: x.upper())
        assert arg.validated('foo', 'foo') == 'FOO'

    def test_use_can_be_list_of_callables(self):
        arg = Arg(use=[lambda x: x.upper(), lambda x: x.strip()])
        assert arg.validated('foo', '  foo  ') == 'FOO'

    def test_convert_and_use_params(self):
        arg = Arg(float, use=lambda val: val + 1)
        assert arg.validated('foo', 41) == 42.0

    def test_error_raised_if_use_is_uncallable(self):
        with pytest.raises(ValueError) as excinfo:
            Arg(use='bad')
        assert '{0!r} is not a callable or list of callables'.format('bad') in str(excinfo)

    def test_use_is_called_before_validate(self):
        arg = Arg(use=lambda x: x + 1, validate=lambda x: x == 41)
        with pytest.raises(ValidationError):
            arg.validated('foo', 41)

    def test_use_can_be_none(self):
        arg = Arg(use=None)
        assert arg.validated('foo', 41) == 41

    def test_validate_can_be_none(self):
        arg = Arg(validate=None)
        assert arg.validated('foo', 41) == 41

    def test_multiple_with_type_arg(self):
        arg = Arg(int, multiple=True)
        assert arg.validated('foo', ['1', 2, 3.0]) == [1, 2, 3]

    def test_multiple_with_use_arg(self):
        arg = Arg(multiple=True, use=lambda x: x.upper())
        assert arg.validated('foo', ['foo', 'bar']) == ['FOO', 'BAR']

    def test_repr(self):
        arg = Arg(str, default='foo', required=True)
        r = repr(arg)
        assert 'str' in r
        assert '<webargs.core.Arg' in r
        assert 'foo' in r
        assert 'required=True' in r

# Parser tests

@mock.patch('webargs.core.Parser.parse_json')
def test_parse_json_called_by_parse_arg(parse_json, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    parse_json.assert_called_with(web_request, 'foo', arg)

@mock.patch('webargs.core.Parser.parse_json')
def test_parse_json_called_with_source(parse_json, web_request):
    arg = Arg(source='bar')
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    parse_json.assert_called_with(web_request, 'bar', arg)

@mock.patch('webargs.core.Parser.parse_querystring')
def test_parse_querystring_called_by_parse_arg(parse_querystring, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    assert parse_querystring.called

@mock.patch('webargs.core.Parser.parse_form')
def test_parse_form_called_by_parse_arg(parse_form, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    assert parse_form.called

@mock.patch('webargs.core.Parser.parse_json')
def test_parse_json_not_called_when_json_not_a_target(parse_json, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request, targets=('form', 'querystring'))
    assert parse_json.call_count == 0

@mock.patch('webargs.core.Parser.parse_headers')
def test_parse_headers_called_when_headers_is_a_target(parse_headers, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    assert parse_headers.call_count == 0
    p.parse_arg('foo', arg, web_request, targets=('headers',))
    parse_headers.assert_called

@mock.patch('webargs.core.Parser.parse_cookies')
def test_parse_cookies_called_when_cookies_is_a_target(parse_cookies, web_request):
    arg = Arg()
    p = Parser()
    p.parse_arg('foo', arg, web_request)
    assert parse_cookies.call_count == 0
    p.parse_arg('foo', arg, web_request, targets=('cookies',))
    parse_cookies.assert_called

@mock.patch('webargs.core.Parser.fallback')
def test_fallback_used_if_all_other_functions_return_none(fallback, web_request):
    arg = Arg()
    p = Parser()
    p.parse({'foo': arg}, web_request)
    fallback.assert_called

@mock.patch('webargs.core.Parser.parse_json')
def test_parse(parse_json, web_request):
    parse_json.return_value = 42
    argmap = {
        'username': Arg(),
        'password': Arg()
    }
    p = Parser()
    ret = p.parse(argmap, web_request)
    assert {'username': 42, 'password': 42} == ret

@mock.patch('webargs.core.Parser.parse_json')
def test_parse_required_arg_raises_validation_error(parse_json, web_request):
    arg = Arg(required=True)
    p = Parser()
    parse_json.return_value = Missing
    with pytest.raises(ValidationError) as excinfo:
        p.parse_arg('foo', arg, web_request)
    assert 'Required parameter ' + repr('foo') + ' not found.' in str(excinfo)

@mock.patch('webargs.core.Parser.parse_json')
def test_parse_required_arg(parse_json, web_request):
    arg = Arg(required=True)
    parse_json.return_value = 42
    p = Parser()
    result = p.parse_arg('foo', arg, web_request, targets=('json', ))
    assert result == 42

@mock.patch('webargs.core.Parser.parse_form')
def test_parse_required_multiple_arg(parse_form, web_request):
    parse_form.return_value = []
    arg = Arg(multiple=True, required=True)
    p = Parser()
    with pytest.raises(ValidationError):
        p.parse_arg('foo', arg, web_request)

    parse_form.return_value = None
    with pytest.raises(ValidationError):
        p.parse_arg('foo', arg, web_request)

def test_default_targets():
    assert set(Parser.DEFAULT_TARGETS) == set(['json', 'querystring', 'form'])


def test_default(parser, web_request):
    web_request.json = {}
    args = {'val': Arg(default='pizza')}
    result = parser.parse(args, web_request, targets=('json', ))
    assert result['val'] == 'pizza'


def test_default_can_be_none(parser, web_request):
    web_request.json = {}
    args = {'val': Arg(default=None)}
    result = parser.parse(args, web_request, targets=('json', ))
    assert result['val'] is None


def test_callable_default(parser, web_request):
    web_request.json = {}
    args = {'val': Arg(default=lambda: 'pizza')}
    result = parser.parse(args, web_request, targets=('json', ))
    assert result['val'] == 'pizza'

def test_value_error_raised_if_invalid_target(web_request):
    arg = Arg()
    p = Parser()
    with pytest.raises(ValueError) as excinfo:
        p.parse_arg('foo', arg, web_request, targets=('invalidtarget', 'headers'))
    assert 'Invalid targets arguments: {0}'.format(['invalidtarget']) in str(excinfo)

@mock.patch('webargs.core.Parser.parse_json')
def test_conversion(parse_json, web_request):
    parse_json.return_value = 42
    arg = Arg(str)
    assert Parser().parse_arg('foo', arg, web_request, targets=('json',)) == '42'

@mock.patch('webargs.core.Parser.handle_error')
@mock.patch('webargs.core.Parser.parse_json')
def test_handle_error_called_when_parsing_raises_error(parse_json, handle_error, web_request):
    val_err = ValidationError('error occurred')
    parse_json.side_effect = val_err
    p = Parser()
    p.parse({'foo': Arg()}, web_request, targets=('json',))
    handle_error.assert_called
    parse_json.side_effect = ValidationError('another exception')
    p.parse({'foo': Arg()}, web_request, targets=('json',))
    assert handle_error.call_count == 2

def test_handle_error_reraises_errors():
    p = Parser()
    with pytest.raises(ValidationError):
        p.handle_error(ValidationError('error raised'))

def test_passing_exception_as_error_argument():
    arg = Arg(int, validate=lambda n: n == 42,
        error=AttributeError('an error occurred.'))
    with pytest.raises(ValidationError) as excinfo:
        arg.validated('foo', 41)
    assert 'an error occurred' in str(excinfo)

@mock.patch('webargs.core.Parser.parse_headers')
def test_targets_as_init_arguments(parse_headers, web_request):
    p = Parser(targets=('headers',))
    p.parse({'foo': Arg()}, web_request)
    assert parse_headers.called

@mock.patch('webargs.core.Parser.parse_files')
def test_parse_files(parse_files, web_request):
    p = Parser()
    p.parse({'foo': Arg()}, web_request, targets=('files',))
    assert parse_files.called

@mock.patch('webargs.core.Parser.parse_json')
def test_custom_error_handler(parse_json, web_request):
    class CustomError(Exception):
        pass

    def error_handler(error):
        raise CustomError(error)
    parse_json.side_effect = ValidationError('parse_json failed')
    p = Parser(error_handler=error_handler)
    with pytest.raises(CustomError):
        p.parse({'foo': Arg()}, web_request)


@mock.patch('webargs.core.Parser.parse_json')
def test_custom_error_handler_decorator(parse_json, web_request):
    class CustomError(Exception):
        pass
    parse_json.side_effect = ValidationError('parse_json failed')

    parser = Parser()

    @parser.error_handler
    def handle_error(error):
        raise CustomError(error)

    with pytest.raises(CustomError):
        parser.parse({'foo': Arg()}, web_request)


def test_custom_target_handler(web_request):
    web_request.data = {'foo': 42}

    parser = Parser()

    @parser.target_handler('data')
    def parse_data(req, name, arg):
        return req.data.get(name)

    result = parser.parse({'foo': Arg(int)}, web_request, targets=('data', ))
    assert result['foo'] == 42

def test_custom_target_handler_with_source(web_request):
    web_request.data = {'X-Foo': 42}
    parser = Parser()

    @parser.target_handler('data')
    def parse_data(req, name, arg):
        # The source name is passed
        assert name == 'X-Foo'
        return req.data.get(name)

    result = parser.parse({'x_foo': Arg(int, source='X-Foo')}, web_request, targets=('data', ))
    assert result['x_foo'] == 42


def test_missing_is_falsy():
    assert bool(Missing) is False

def test_full_input_validation(web_request):

    web_request.json = {'foo': 41, 'bar': 42}

    parser = MockRequestParser()
    args = {'foo': Arg(int), 'bar': Arg(int)}
    with pytest.raises(ValidationError):
        # Test that `validate` receives dictionary of args
        parser.parse(args, web_request, targets=('json', ),
                     validate=lambda args: args['foo'] > args['bar'])

def test_full_input_validation_with_multiple_validators(web_request, parser):
    def validate1(args):
        if args['a'] > args['b']:
            raise ValidationError('b must be > a')

    def validate2(args):
        if args['b'] > args['a']:
            raise ValidationError('a must be > b')

    args = {'a': Arg(int), 'b': Arg(int)}
    web_request.json = {'a': 2, 'b': 1}
    validators = [validate1, validate2]
    with pytest.raises(ValidationError) as excinfo:
        parser.parse(args, web_request, targets=('json', ),
                validate=validators)
    assert 'b must be > a' in str(excinfo)

    web_request.json = {'a': 1, 'b': 2}
    with pytest.raises(ValidationError) as excinfo:
        parser.parse(args, web_request, targets=('json', ),
                validate=validators)
    assert 'a must be > b' in str(excinfo)

def test_full_input_validation_with_custom_error(web_request):
    web_request.json = {'foo': 41}
    parser = MockRequestParser(error='cool custom message')
    args = {'foo': Arg(int)}
    with pytest.raises(ValidationError) as excinfo:
        # Test that `validate` receives dictionary of args
        parser.parse(args, web_request, targets=('json', ),
                     validate=lambda args: False)
    assert 'cool custom message' in str(excinfo)

def test_full_input_validator_receives_nonascii_input(web_request):
    def validate(val):
        return False
    text = u'øœ∑∆∑'
    web_request.json = {'text': text}
    parser = MockRequestParser()
    args = {'text': Arg(unicode)}
    with pytest.raises(ValidationError):
        parser.parse(args, web_request, targets=('json', ), validate=validate)

def test_parse_with_source(web_request):

    web_request.json = {'foo': 41, 'bar': 42}

    parser = MockRequestParser()
    args = {'foo': Arg(int), 'baz': Arg(int, source='bar')}
    parsed = parser.parse(args, web_request, targets=('json',))
    assert parsed == {'foo': 41, 'baz': 42}

def test_metadata_can_be_stored_on_args():
    # Extra params are stored as metadata
    arg = Arg(int, description='Just a number.')
    assert arg.metadata['description'] == 'Just a number.'

def test_use_args(web_request, parser):
    user_args = {
        'username': Arg(str),
        'password': Arg(str)
    }
    web_request.json = {'username': 'foo', 'password': 'bar'}

    @parser.use_args(user_args, web_request)
    def viewfunc(args):
        return args
    assert viewfunc() == {'username': 'foo', 'password': 'bar'}

def test_use_kwargs(web_request, parser):
    user_args = {
        'username': Arg(str),
        'password': Arg(str),
    }
    web_request.json = {'username': 'foo', 'password': 'bar'}

    @parser.use_kwargs(user_args, web_request)
    def viewfunc(username, password):
        return {'username': username, 'password': password}
    assert viewfunc() == {'username': 'foo', 'password': 'bar'}


def test_use_kwargs_with_arg_missing(web_request, parser):
    user_args = {
        'username': Arg(str),
        'password': Arg(str),
    }
    web_request.json = {'username': 'foo'}

    @parser.use_kwargs(user_args, web_request)
    def viewfunc(username, password):
        return {'username': username, 'password': password}
    assert viewfunc() == {'username': 'foo', 'password': None}

def test_use_kwargs_with_arg_allowed_missing(web_request, parser):
    user_args = {
        'username': Arg(str),
        'password': Arg(str, allow_missing=True),
    }
    web_request.json = {'username': 'foo'}

    @parser.use_kwargs(user_args, web_request)
    def viewfunc(username, password):
        return {'username': username, 'password': password}
    assert viewfunc() == {'username': 'foo', 'password': None}

def test_validation_errors_in_validator_are_passed_to_handle_error(parser, web_request):
    def validate(value):
        raise ValidationError('Something went wrong.')
    args = {
        'name': Arg(validate=validate, target='json')
    }
    web_request.json = {'name': 'invalid'}
    with pytest.raises(ValidationError) as excinfo:
        parser.parse(args, web_request)
    exc = excinfo.value
    assert isinstance(exc, ValidationError)
    assert str(exc) == 'Something went wrong.'

def test_multiple_validators_may_be_specified_for_an_arg(parser, web_request):
    def validate_len(val):
        if len(val) < 6:
            raise ValidationError('Must be greater than 6 characters.')

    def has_digit(val):
        if not any(ch.isdigit() for ch in val):
            raise ValidationError('Must have a digit.')
    args = {
        'password': Arg(validate=[validate_len, has_digit])
    }
    web_request.json = {'password': '123'}
    with pytest.raises(ValidationError) as excinfo:
        parser.parse(args, web_request)
    assert 'Must be greater than 6 characters.' in str(excinfo)

    web_request.json = {'password': 'abcdefhij'}
    with pytest.raises(ValidationError) as excinfo:
        parser.parse(args, web_request)
    assert 'Must have a digit.' in str(excinfo)

def test_error_raised_if_validate_is_uncallable():
    with pytest.raises(ValueError) as excinfo:
        Arg(validate='uncallable')
    assert '{0!r} is not a callable or list of callables.'.format('uncallable') in str(excinfo)


class TestValidationError:

    def test_can_store_status_code(self):
        err = ValidationError('foo', status_code=401)
        assert err.status_code == 401

    def test_can_store_extra_data(self):
        err = ValidationError('foo', headers={'X-Food-Header': 'pizza'})
        assert err.data['headers'] == {'X-Food-Header': 'pizza'}

    def test_str(self):
        err = ValidationError('foo', status_code=403)
        assert str(err) == 'foo'

    def test_repr(self):
        err = ValidationError('foo', status_code=403)
        assert repr(err) == ('ValidationError({0!r}, '
                'status_code=403)'.format(unicode('foo')))
