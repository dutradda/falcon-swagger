from falconswagger import SwaggerAPI, ModelHttpMeta


class HelloModelMeta(ModelHttpMeta):
   __schema__ = {
      '/hello/you/{name}': {
         'get': {
            'parameters': [{
                'name': 'name',
                'in': 'path',
                'required': True,
                'type': 'string'
            }],
            'operationId': 'get_hello_you',
            'responses': {'200': {'description': 'Got you'}}
        }
      },
      '/hello/world': {
         'get': {
            'operationId': 'get_hello_world',
            'responses': {'200': {'description': 'Got hello'}}
        }
      }
   }

   def get_hello_you(cls, req, resp):
      you = req.context['parameters']['uri_template']['name']
      resp.body = 'Hello {}!\n'.format(you)
                  
   def get_hello_world(cls, req, resp):
      resp.body = 'Hello World!\n'


class HelloModel(metaclass=HelloModelMeta):
   pass


api = SwaggerAPI([HelloModel], title='Hello API')
