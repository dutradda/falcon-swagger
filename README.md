[![Build Status](https://travis-ci.org/dutradda/falcon-swagger.svg?branch=master)](https://travis-ci.org/dutradda/falcon-swagger)
[![Coverage Status](https://coveralls.io/repos/github/dutradda/falcon-swagger/badge.svg?branch=master)](https://coveralls.io/github/dutradda/falcon-swagger?branch=master)

# falcon-swagger
A Falcon Framework (http://falconframework.org) Extension.

Features:
- Supports Swagger Schema 2.0 (OpenAPI 2.0);
- Provides SQLAlchemy models base classes (with Redis integration, if you want);
- Provides Redis models base classes (without SQLAlchemy).

Usage Example:

```python
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
```

```bash
gunicorn hello_word_api:api
```

```bash
curl -i localhost:8000/hello/world
```

```text
HTTP/1.1 200 OK
Server: gunicorn/19.6.0
Connection: close
content-length: 13
content-type: application/json; charset=UTF-8

Hello World!
```

```bash
curl -i localhost:8000/hello/you/Diogo
```

```text
HTTP/1.1 200 OK
Server: gunicorn/19.6.0
Connection: close
content-length: 13
content-type: application/json; charset=UTF-8

Hello Diogo!
```


```bash
curl -i localhost:8000/swagger.json
```

```json
HTTP/1.1 200 OK
Server: gunicorn/19.6.0
Connection: close
content-length: 672
content-type: application/json; charset=UTF-8

{
  "swagger": "2.0",
  "paths": {
    "/hello/world": {
      "get": {
        "operationId": "HelloModel.get_hello_world",
        "responses": {
          "200": {
            "description": "Got hello"
          }
        }
      }
    },
    "/hello/you/{name}": {
      "get": {
        "operationId": "HelloModel.get_hello_you",
        "responses": {
          "200": {
            "description": "Got you"
          }
        },
        "parameters": [
          {
            "in": "path",
            "type": "string",
            "required": true,
            "name": "name"
          }
        ]
      }
    }
  },
  "info": {
    "title": "Hello API",
    "version": "1.0.0"
  }
}
```
