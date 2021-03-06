from . import app
from flask import Markup
import mistune as md
import pytz

@app.template_filter()
def dateformat(date, timezone):
    if not date:
        return None
    tz = pytz.timezone(timezone)
    utc = pytz.timezone('UTC')
    tz_aware_dt = utc.localize(date)
    local_dt = tz_aware_dt.astimezone(tz)
        
    return local_dt.strftime('%a %b %d %I:%M:%S %p %Y')