from minecontrol import app


app.config['DEBUG']=True
app.config['SECRET_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/minecontrol.db'

app.run()

