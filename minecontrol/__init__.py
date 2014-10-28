from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CsrfProtect
from flask.ext.security import Security, SQLAlchemyUserDatastore

app = Flask(__name__)
db = SQLAlchemy(app)

CsrfProtect(app)

app.config['SECRET_KEY'] = 'super-secret'
app.config['API_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/minecontrol.db'
app.config['MY_URL'] = 'http://localhost:5000'

#set TWITTER_TOKEN and TWITTER_SECRET for tweet support

# celery config
app.config['CELERY_BROKER_URL']='redis://localhost:6379'
app.config['CELERY_RESULT_BACKEND']='redis://localhost:6379'

app.config['SECURITY_CHANGEABLE'] = True
app.config['SECURITY_SEND_PASSWORD_CHANGE_EMAIL'] = False
# enable hashed passwords
app.config['SECURITY_PASSWORD_HASH'] = 'sha512_crypt'
# remember to override SECURITY_PASSWORD_SALT
app.config['SECURITY_PASSWORD_SALT'] = '2FZcxCHezFY2j0QVC6sq'

app.config['DEFAULT_ADMIN_PASS'] = 'changeme'

# load local configuration
app.config.from_pyfile('../my.cfg', silent=True)

# For AWS Control ~/.boto or /etc/boto.cfg must exist.
# see https://aws.amazon.com/articles/Python/3998

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler 
    file_handler = RotatingFileHandler('minecontrol.log',maxBytes=30000000)
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

import minecontrol.models

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
security = Security(app, user_datastore)

@app.before_first_request
def dbinit():
  global user_datastore

  # ensure db created
  db.create_all()
  db.session.commit()

  if db.session.query(models.User).count() == 0:
    admin_user = user_datastore.create_user(email='admin', password=app.config['DEFAULT_ADMIN_PASS'])
    user_datastore.create_role(name='member', description='Member of this server')
    admin_group = user_datastore.create_role(name='admin', \
        description='Administrator of this server')
    user_datastore = user_datastore.add_role_to_user(admin_user, admin_group)
    db.session.commit()

import minecontrol.views
import mycelery
