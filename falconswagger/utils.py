from jsonschema import Draft4Validator, RefResolver
import os.path
import json
import sys


def build_validator(schema, path):
    handlers = {'': _URISchemaHandler(path)}
    resolver = RefResolver.from_schema(schema, handlers=handlers)
    return Draft4Validator(schema, resolver=resolver)


class _URISchemaHandler(object):

    def __init__(self, schemas_path):
        self._schemas_path = schemas_path

    def __call__(self, uri):
        schema_filename = os.path.join(self._schemas_path, uri.lstrip('/'))
        with open(schema_filename) as json_schema_file:
            return json.load(json_schema_file)


def get_dir_path(filename):
    return os.path.dirname(os.path.abspath(filename))


def get_model_schema(filename, schema_name='schema.json'):
    return json.load(open(os.path.join(get_dir_path(filename), schema_name)))


def get_module_path(cls):
    module_filename = sys.modules[cls.__module__].__file__
    return get_dir_path(module_filename)
