import os
from flask_script import Manager

from visitor_pass import app
from getpass import getpass
from werkzeug.security import generate_password_hash

from visitor_pass.database import Base, session, Building, Pass, User

manager = Manager(app)

@manager.command
def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)
    
@manager.command
def building_seed():
    building1 = Building(building_name="M3",
                        building_address="1188 Pinetree Way,Coquitlam, BC, Canada", licenses=10)
    
    building2 = Building(building_name="QuayWest II",
                        building_address="1067 Marinaside Crescent,Vancouver, BC, Canada",
                        licenses=100, contact_name="Tom Dirsh", contact_phone="604 111 1111")
    
    
    building3 = Building(building_name="M2",
    building_address="3008 Glen Drive, Coquitlam, BC, Canada", licenses=10)
    session.add_all([building1, building2, building3])
    session.commit()

@manager.command
def pass_seed():
    pass1 = Pass(pass_id="243", pass_maxtime=1440, building_id=1,
    license_plate="145NEW", email_1="jamiegill.03@gmail.com", resident_id=1)
    pass2 = Pass(pass_id="253", pass_maxtime=1440, building_id=1)
    pass3 = Pass(pass_id="A2D345", pass_maxtime=2880, building_id=2,
    license_plate="456QWE", email_1="test@gmail.com")
    session.add_all([pass1, pass2, pass3])
    session.commit()
    
@manager.command
def adduser():
    name = input("Name: ")
    email = input("Email: ")
    if session.query(User).filter_by(email=email).first():
        print("User with that email address already exists")
        return
    
    password = ""
    while len(password) < 8 or password != password_2:
        password = getpass("Password: ")
        password_2 = getpass("Re-enter password: ")
    user = User(name=name, email=email,
                password=generate_password_hash(password))
    session.add(user)
    session.commit() 

class DB(object):
    def __init__(self, metadata):
        self.metadata = metadata


if __name__ == "__main__":
    manager.run()