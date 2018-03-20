import os
from flask_script import Manager

from visitor_pass import app
from getpass import getpass
from werkzeug.security import generate_password_hash
import string
import random

from visitor_pass.database import Base, session, Building, Pass, User

manager = Manager(app)

@manager.command
def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)
    
@manager.command
def building_seed():
    building1 = Building(name="M3", used_licenses=0,
                        address="1188 Pinetree Way,Coquitlam, BC, Canada", total_licenses=3)
    
    building2 = Building(name="QuayWest II", used_licenses=0,
                        address="1067 Marinaside Crescent,Vancouver, BC, Canada",
                        total_licenses=100, contact_name="Tom Dirsh", contact_phone="604 111 1111")
    
    
    building3 = Building(name="M2", used_licenses=0,
    address="3008 Glen Drive, Coquitlam, BC, Canada", total_licenses=10)
    session.add_all([building1, building2, building3])
    session.commit()

@manager.command
def pass_seed():
    pass1 = Pass(pass_id="243", maxtime=1440, building_id=1,
    license_plate="145NEW", email_1="jamiegill.03@gmail.com", resident_id=1)
    pass2 = Pass(pass_id="253", maxtime=1440, building_id=1)
    pass3 = Pass(pass_id="A2D345", maxtime=2880, building_id=2,
    license_plate="456QWE", email_1="test@gmail.com")
    session.add_all([pass1, pass2, pass3])
    session.commit()
    
@manager.command
def adduser():
    name = input("Name: ")
    email = input("Email: ")
    phone = input("Phone: ")
    building_name = input("building for this user: ")
    building_exists = session.query(Building).filter_by(name=building_name).first()
    if not building_exists:
        print("This is not an existing building")
        return
    building_id = building_exists.id
    privilege = []
    while privilege not in ("admin", "general", "read_only"):
        privilege = input("Privilege (ie. general OR admin OR read_only): ")
    # "general" is a building resident, "admin" is the concierge, "read_only" is the parking pass verifyer
    if session.query(User).filter_by(email=email).first():
        print("User with that email address already exists")
        return
    # Create 6 digit password
    password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
    user = User(name=name, email=email, phone=phone, privilege=privilege, building_id=building_id,
                password=generate_password_hash(password))
    session.add(user)
    session.commit() 
    print("user added. Auto-generated password is {}".format(password))
    
def addbuilding():
        name = input("Building name: ")
        if session.query(Building).filter_by(name=name).first():
            print("Building with that name already exists")
            return
        timezone = input("Timezone(eg. US/Eastern): ")
        address = input("Address: ")
        total_licenses = int(input("Licenses: "))
        contact_name = input("Building contact name: ")
        contact_phone = input("Building contact phone number: ")
        building = Building(name=name, address=address, total_licenses=total_licenses,
                            contact_name=contact_name, contact_phone=contact_phone,
                            used_licenses=0, timezone=timezone
        )
        session.add(building)
        session.commit()
        
class DB(object):
    def __init__(self, metadata):
        self.metadata = metadata


if __name__ == "__main__":
    manager.run()