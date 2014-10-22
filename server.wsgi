APP_PATH="/var/www/mc-aws-cp/"
import sys
sys.path.insert(0,APP_PATH)
activate_this = APP_PATH + '.env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
from minecontrol import app as application
