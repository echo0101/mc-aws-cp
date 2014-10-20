from minecontrol import app
from flask.ext.security import login_required

@app.route('/')
@login_required
def index():
      return 'Hello World!'
