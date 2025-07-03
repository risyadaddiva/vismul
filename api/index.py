from app.app import get_app
from vercel_wsgi import handle_request

def handler(environ, start_response):
    app = get_app()
    return handle_request(app, environ, start_response)