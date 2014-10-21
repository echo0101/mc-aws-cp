from minecontrol import app

app.config['SECRET_KEY'] = 'super-secret'
app.config['API_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/minecontrol.db'

# Local configuration file
#  - set DEBUG = True for debugging
#  - set API_KEY for api key
app.config.from_pyfile('../my.cfg', silent=True)

# For AWS Control ~/.boto or /etc/boto.cfg must exist.
# see https://aws.amazon.com/articles/Python/3998

app.run()

