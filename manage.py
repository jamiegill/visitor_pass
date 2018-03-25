import os
from flask_script import Manager

from visitor_pass import app
from getpass import getpass
from werkzeug.security import generate_password_hash
import string
import random
from visitor_pass.views import db_commit_check

from visitor_pass.database import Base, session, Building, Pass, User

manager = Manager(app)

@manager.command
def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)
    
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
    db_commit_check(building_id, "su", "ADMIN_COMMIT - adduser: name={} email={} phone={} privilege={} building_id={} password={}"
        .format(name, email, phone, privilege, building_id, password)) 

    print("user added. Auto-generated password is {}".format(password))
 
@manager.command    
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
                            used_licenses=0, timezone=timezone)
        session.add(building)
        #Be careful with this commit, there is no check for this (because building_id isnt' created yet)
        session.commit()

@manager.command
def delete_item():


    delete_item = []
    while delete_item not in ("Building", "User", "Pass"):
        delete_item = input("Specify 'Building', 'User' or 'Pass': ")
    
    item_id = input("What is the {} ID: ".format(delete_item))



    if delete_item == "Pass":
        if session.query(Pass).filter_by(id=item_id).first():
            item_data = session.query(Pass).filter_by(id=item_id).first()
            building_id = item_data.building_id

            log_msg = ("ID = {}, Unit = {}, resident_id = {}".format(item_data.pass_id, item_data.unit, item_data.resident_id))
            print(log_msg)
        else:
            print("Please check if {} ID: {} actually exists".format(delete_item, item_id))
            exit()

    if delete_item == "User":
        if session.query(User).filter_by(id=item_id).first():
            item_data = session.query(User).filter_by(id=item_id).first()
            building_id = item_data.building_id
            log_msg = ("Name = {}, Email = {}, Phone = {} Privilege = {}".format(item_data.name, item_data.email, item_data.phone, item_data.privilege))
            print(log_msg)
        else:
            print("Please check if {} ID: {} actually exists".format(delete_item, item_id))
            exit()

        #make sure no Pass is dependant on this User
        if session.query(Pass).filter_by(resident_id=item_id).first():
            pass_id = session.query(Pass).filter_by(resident_id=item_id).first().id
            print("You must remove passes before deleting the user --> look at Pass ID {}".format(pass_id))
            exit()


    if delete_item == "Building":
        if session.query(Building).filter_by(id=item_id).first():
            item_data = session.query(Building).filter_by(id=item_id).first()
            building_id = item_id

            log_msg = ("Name = {}, Address = {}, Contact Name = {}, Contact Phone = {}, Total Licenses = {}, Used Licenses = {}, Timezone = {}, Creation_date = {}".format(
                item_data.name, item_data.address, item_data.contact_name, item_data.contact_phone, item_data.total_licenses, item_data.used_licenses, 
                item_data.timezone, item_data.creation_date))

            print(log_msg)
            print("NOTE: If you proceed to delete the building, don't worry about the NoneType error it will throw --> this occurs because the building_id disappears, it's expected behavior")
        else:
            print("Please check if {} ID: {} actually exists".format(delete_item, item_id))
            exit()

        #make sure no User is dependant on this Building
        if session.query(User).filter_by(building_id=item_id).first():
            user_id = session.query(User).filter_by(building_id=item_id).first().id
            print("You must remove users before deleting the building --> look at User ID {}".format(user_id))
            exit()



    confirm_delete = []
    while confirm_delete != "YES":
        confirm_delete = input("Type 'YES' to execute deletion:")

    session.delete(item_data)
    db_commit_check(building_id, "su", "ADMIN_COMMIT - delete{} {}".format(delete_item, log_msg))



class DB(object):
    def __init__(self, metadata):
        self.metadata = metadata


if __name__ == "__main__":
    manager.run()