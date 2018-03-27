import os
import threading


from flask import Flask

app = Flask(__name__)
config_path = os.environ.get("CONFIG_PATH", "visitor_pass.config.DevelopmentConfig")
app.config.from_object(config_path)

from . import views
from . import filters
from . import login

#This spawns the function plate_datetime() in it's own thread

plate_datetime_thread = threading.Thread(target=views.plate_datetime)
plate_datetime_thread.start()

