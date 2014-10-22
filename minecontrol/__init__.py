from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)

app.config['SECRET_KEY'] = 'super-secret'
app.config['API_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/minecontrol.db'
app.config['MY_URL'] = 'http://localhost'

# Local configuration file
#  - set DEBUG = True for debugging
#  - set API_KEY for api key
#  - set MY_URL to accessible url to recieve stats
app.config.from_pyfile('../my.cfg', silent=True)

# For AWS Control ~/.boto or /etc/boto.cfg must exist.
# see https://aws.amazon.com/articles/Python/3998

import minecontrol.views
import minecontrol.models

