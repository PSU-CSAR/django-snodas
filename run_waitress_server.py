import os
from waitress import serve
from snodas.wsgi import application
serve(application,host="0.0.0.0",port=os.environ["PORT"],url_scheme='https')
