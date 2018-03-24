from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user, logout_user
from .login import load_user
import random
import datetime
from . import app
from .database import session, Pass, Building, User
from .send_email import *
from .filters import *
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
import string


import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('logs/logger.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def db_commit_check(building_id, log_userid, field_update):
    try:
        #session.flush()
        session.commit()
        commit_status = "commit success - "
    except :
        session.rollback()
        flash ("Change not made: {}".format(field_update), "danger")
        commit_status = "Exception - "
    
    building_id = session.query(Building).filter(Building.id == building_id).first()
    building_name = building_id.name
    logger.debug("{}:uid {}:{}{}".format(building_name, log_userid, commit_status, field_update))

def plate_datetime(passes):
    # See if timestamp has expired
    curr_time=datetime.datetime.now()
    for record in passes:
        record_id = record.id
        record = record.plate_expire
        if record == None:
            pass
        elif curr_time > record:
            pass_record = session.query(Pass).filter(Pass.id == record_id).first()
            pass_record.plate_expire = None
            pass_record.license_plate = None
            pass_record.email_1 = None
            pass_record.email_2 = None
            session.add(pass_record)
            db_commit_check(pass_record.building_id,"sys","AutoEndPass PassID = {}, Pass = {}, License Plate = {}, Plate Expire = {}".format(pass_record.id, pass_record.pass_id, pass_record.license_plate, pass_record.plate_expire))

@app.route("/")
@login_required
def get_root():
    building_id = current_user.building_id
    return redirect(url_for("get_passes", building_id=building_id))

@app.route("/passes/<int:building_id>/", methods=["GET","POST"])
@login_required
def get_passes(building_id):

    

    search_string = ""
    if request.method == 'POST':
        search_string = request.form["search"]
    search_var = "%{}%".format(search_string)
            
    
    """ List of passes for a building """
    # Permit/deny access to page depening on logged in user
    if current_user.privilege in ("admin", "superuser") and current_user.building_id == building_id:
        access_priv = "admin"
    elif current_user.privilege in ("read_only") and current_user.building_id == building_id:
        access_priv = "read_only"
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    # Join the User and Pass table together, foreign key is Pass.resident_id
    #passes = session.query(User.email, User.name, User.phone, Pass.id, Pass.unit, Pass.pass_id, Pass.license_plate, Pass.plate_expire).join(Pass, Pass.resident_id == User.id).filter(Pass.building_id == building_id)
    passes = session.query(User.email, User.name, User.phone, Pass.id, Pass.unit, Pass.pass_id, Pass.license_plate, Pass.plate_expire).join(Pass, Pass.resident_id == User.id).filter(or_(User.email.like(search_var), User.name.like(search_var), User.phone.like(search_var),Pass.unit.like(search_var),Pass.pass_id.like(search_var),Pass.license_plate.like(search_var)))

    
    # find building details
    building = session.query(Building).filter(Building.id == building_id).first()
    # find user details
    
    plate_datetime(passes)
    return render_template("view_passes.html",
    passes=passes,
    building=building,
    access_priv=access_priv,
    search_string=search_string
    )

@app.route("/passes/<int:building_id>/", methods=["GET","POST"])
@login_required
def pass_search_get(building_id):
    if request.method == 'POST':
        print(request.form["search"])
    return redirect(url_for("get_passes", building_id=building_id))


@app.route("/passes/<int:building_id>/add", methods=["GET"])
@login_required
def add_pass_get(building_id):
    
    # Permit/deny access to page depening on logged in user
    if current_user.privilege in ("admin", "superuser") and current_user.building_id == building_id:
        pass
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    building = session.query(Building)
    building = building.filter(Building.id == building_id).first()
    total_licenses = building.total_licenses
    used_licenses = session.query(Pass).filter(Pass.building_id == building_id).count()
    if used_licenses >= total_licenses:
        flash ("Max licenses used. Please delete users or purchase more licenses", "warning")
        return redirect(url_for("get_passes", building_id=building_id))
            
    return render_template("add_pass.html",
    building=building,
    used_licenses=used_licenses
    )
    
@app.route("/passes/<int:building_id>/add", methods=["POST"])
def add_pass_post(building_id):
    # Check for duplicate pass_id
    
    try:
        building=session.query(Pass).filter(Pass.building_id == building_id)
        building.filter(Pass.pass_id.like(request.form["pass_id"])).first().pass_id
        flash ("Pass \"{}\" has already been added, please add a new pass".format(request.form["pass_id"]), "warning")
        return redirect(url_for("add_pass_get", building_id=building_id))
    except AttributeError:
        pass
    
    
    # Check for duplicate email
    try:
        session.query(User).filter(User.email.like(request.form["email"])).first().email
        flash ("Adding pass to existing email: {}".format(request.form["email"]), "info")
        added_userid=session.query(User).filter(User.email.like(request.form["email"])).first().id
        
    except AttributeError:
        # Add new email address to the DB
        password = []
        password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
        add_email = User(
        email=request.form["email"],
        phone=request.form["phone"],
        name=request.form["name"],
        privilege="general",
        password=generate_password_hash(password),
        building_id=building_id
        )
        session.add(add_email)
        db_commit_check(building_id,current_user.id,"Add New Email = {}, Name = {}, Phone = {}".format(request.form["email"], request.form["name"], request.form["phone"]))
        building_name=session.query(Building).filter(Building.id == building_id).first().name
        flash ("Pass and user created - {} has been emailed with the Username and Password specified below".format(request.form["email"]), "success")
        flash ("Username: {}   |   Password: {}".format(request.form["email"], password), "info")

        email_subject = "Welcome to VPass Portal, {}".format(request.form["name"])
        email_address_add(building_name,request.form["name"], request.form["email"], password, email_subject)
        # Once email is added to DB, get the latest "added userid" and use this for next DB addition
        added_userid=session.query(User.id).order_by(User.id.desc()).first()[0]
    
    

    
    # Add a pass to the DB 
    add_pass = Pass(
        pass_id=request.form["pass_id"],
        maxtime=request.form["maxtime"],
        unit=request.form["unit"],
        building_id=building_id,
        resident_id=added_userid
    )
    building = session.query(Building).filter(Building.id == building_id).first()
    session.add_all([add_pass, building])
    
    db_commit_check(building_id,current_user.id,"Add New Pass = {}, Expiry Timer = {}, Unit = {}, ResID = {}".format(request.form["pass_id"],
    request.form["maxtime"], request.form["unit"], added_userid))
    
    
    return redirect(url_for("get_passes", building_id=building_id))

@app.route("/passes/<int:pass_id>/edit", methods=["GET"])
@login_required
def edit_pass_get(pass_id):
        # Permit/deny access to page depening on logged in user
#    if current_user.privilege in ("admin", "superuser") and current_user.building_id == building_id:
#        pass
#    else:
#        flash ("Authorization Error - redirected to login page", "danger")
#        return redirect(url_for("login_get"))
    
    this_pass = session.query(Pass.pass_id, Pass.unit, Pass.maxtime, User.email, User.name, User.phone).join(User, User.id == Pass.resident_id).filter(Pass.id == pass_id).first()
            
    return render_template("edit_pass.html",
    this_pass=this_pass
    )
    
@app.route("/passes/<int:pass_id>/edit", methods=["POST"])
def edit_pass_post(pass_id):
    
    pass_list = []
    user_list = []
    
    # Make changes to items in the "passes" DB table
    pass_num = request.form["pass_id"]
    unit = request.form["unit"]
    maxtime = request.form["maxtime"]
    
    
    edit_pass = session.query(Pass).filter(Pass.id == pass_id).first()
    building_id=edit_pass.building_id
    
    if len(pass_num) > 0 and edit_pass.pass_id != pass_num:
        try:
            building=session.query(Pass).filter(Pass.building_id == building_id)
            building.filter(Pass.pass_id.like(request.form["pass_id"])).first().pass_id
            flash ("Pass \"{}\" has already been added, please add a new pass".format(pass_num), "warning")
        except AttributeError:
            edit_pass_num = edit_pass
            edit_pass_num.pass_id = pass_num
            session.add(edit_pass_num)
            db_commit_check(building_id,current_user.id,"Edit PassID = {}, Pass = {}".format(pass_id, pass_num))
            pass_list.append("Pass Number = {}".format(pass_num))
            
        
    if len(unit) > 0 and edit_pass.unit != unit:
        edit_pass_unit = edit_pass
        edit_pass_unit.unit = unit
        session.add(edit_pass_unit)
        db_commit_check(building_id,current_user.id,"Edit PassID = {}, Pass = {}, Unit = {}".format(pass_id,edit_pass_unit.pass_id, unit))
        pass_list.append("Unit = {}".format(unit))
        
    if len(maxtime) > 0 and edit_pass.maxtime != maxtime:
        edit_pass_maxtime = edit_pass
        edit_pass_maxtime.maxtime = maxtime
        session.add(edit_pass_maxtime)
        db_commit_check(building_id,current_user.id,"Edit PassID = {}, Pass = {}, Expiry Timer = {}".format(pass_id, edit_pass_maxtime.pass_id, maxtime))
        pass_list.append("Expiry Timer = {}".format(maxtime))
        
    # Make changes to items in the "users" DB table
    name = request.form["name"]
    phone = request.form["phone"]
    email = request.form["email"]
    
    user_id = edit_pass.resident_id
    edit_user = session.query(User).filter(User.id == user_id).first()
    prev_user = edit_user
    
    
    if len(email) > 0 and edit_user.email != email:
            # Check for duplicate email elsewhere in the system
        try:
            session.query(User).filter(User.email.like(request.form["email"])).first().email
            flash ("Adding pass to existing email: {}".format(request.form["email"]), "info")
        
        except AttributeError:
            # Add new email address to the DB --> existing user and phone number must follow
            password = []
            password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
            add_email = User(
            building_id = building_id,
            email=request.form["email"],
            name=edit_user.name,
            phone=edit_user.phone,
            privilege="general",
            password=generate_password_hash(password),
            )
            session.add(add_email)
            db_commit_check(building_id,current_user.id,"Edit New Email = {}, Name = {}, Phone = {}".format(email, edit_user.name, edit_user.phone))
            building_name=session.query(Building).filter(Building.id == building_id).first().name

            email_subject = "VPass Portal - Username Change initiated by administrator"

            email_address_add(building_name,request.form["name"], request.form["email"], password, email_subject)
            flash ("{} has been emailed with the Username and Password specified below".format(request.form["email"]), "success")
            flash ("Username: {}   |   Password: {}".format(request.form["email"], password), "info")
        
        new_email = session.query(User).filter(User.email.like(request.form["email"])).first()    
        new_email_id = new_email.id
        edit_pass_resident_id = edit_pass
        edit_pass_resident_id.resident_id = new_email_id
        session.add(edit_pass_resident_id)
        db_commit_check(building_id,current_user.id,"Edit PassID = {} Pass = {}, Resident ID = {}, Email = {}".format(pass_id, edit_pass.pass_id, new_email_id, new_email.email))
        user_list.append("Email = {}".format(email))
        # Check the PREVIOUS email address and remove if NO passes are assigned to that UserID
        pass_count = session.query(Pass).filter(Pass.resident_id == prev_user.id).count()
        print(pass_count)
        if pass_count == 0:
            session.delete(prev_user)
            db_commit_check(building_id,current_user.id,"Delete User = {}, Email = {} due to 0 passes assigned to User".format(prev_user.id, prev_user.email))
    
    #Query current pass and user details (in case the resident ID has changed from the duplicate email check above (ie. try statement))
    edit_pass = session.query(Pass).filter(Pass.id == pass_id).first()
    user_id = edit_pass.resident_id
    edit_user = session.query(User).filter(User.id == user_id).first()
    
    if len(name) > 0 and edit_user.name != name:
        edit_user_name = edit_user
        edit_user_name.name = name
        session.add(edit_user_name)
        db_commit_check(building_id,current_user.id,"Edit UserID = {}, Email = {}, Name = {}".format(user_id, edit_user_name.email, name))
        user_list.append("Name = {}".format(name))

    if len(phone) > 0 and edit_user.phone !=phone:
        edit_user_phone = edit_user
        edit_user_phone.phone = phone
        session.add(edit_user_phone)
        db_commit_check(building_id,current_user.id,"Edit UserID = {}, Email = {}, Phone = {}".format(user_id, edit_user_phone.email, phone))
        user_list.append("Phone = {}".format(phone))
      
    if len(pass_list) > 0:
        current_pass_num = edit_pass.pass_id
        pass_check = [s for s in pass_list if "Number" in s]
        if len(pass_check) == 0:
            pass_list.insert(0, "Pass Number = {}".format(current_pass_num))
        pass_list_output = ",".join(pass_list)
        flash ("Changes to Pass: {}".format(pass_list_output), "info")
        
    if len(user_list) > 0:
        current_user_email = edit_user.email
        email_check = [s for s in user_list if "Email" in s]
        if len(email_check) == 0:
            user_list.insert(0, "Email = {}".format(current_user_email))    
        user_list_output = ",".join(user_list)
        flash ("Changes to user account: {}".format(user_list_output), "info")
        
    return redirect(url_for("edit_pass_post", pass_id=pass_id))

@app.route("/passes/<int:pass_id>/delete", methods=["GET"])
@login_required
def delete_pass_get(pass_id):
    delete_email = []
    
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
    # Permit/deny access to page depening on logged in user
    if current_user.privilege in ("admin", "superuser") and current_user.building_id == pass_data.building_id:
        pass
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    user_data = session.query(User).filter(User.id == pass_user_id).first()
    
    # See how many resident_id instances are found for this pass
    # jinja will choose whether to delete the email address or not
    user_instances = len(session.query(Pass.pass_id).filter(Pass.resident_id == pass_user_id).all())
    if user_instances == 1:
        delete_email = True
    else:
        delete_email = False
        
    # Provide building details for redirect
    building_id = pass_data.building_id
    
    
    return render_template("delete_pass.html",
    pass_data=pass_data,
    user_data=user_data,
    delete_email=delete_email,
    building_id=building_id
    )
    
@app.route("/passes/<int:pass_id>/delete", methods=["POST"])
def delete_pass_post(pass_id):
    """ Delete Pass, Delete User """
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    user_data = session.query(User).filter(User.id == pass_user_id).first()
    
    # Delete the pass
    session.delete(pass_data)
    
    # Obtain building ID and remove license
    building_id = pass_data.building_id
    building = session.query(Building).filter(Building.id == building_id).first()
    session.add(building)
    db_commit_check(building_id,current_user.id,"Delete PassID = {}, Pass = {}".format(pass_id, pass_data.pass_id))
    
    
    # Delete the user if only 1 instance is found in the passes DB
    user_instances = len(session.query(Pass).filter(Pass.resident_id == pass_user_id).all())
    if user_instances == 0:
        user_data = session.query(User).filter(User.id == pass_user_id).first()
        session.delete(user_data)
        db_commit_check(building_id,current_user.id,"Delete User = {}, Email = {} due to Pass = {} deletion".format(pass_user_id,user_data.email, pass_id))
        flash ("Pass and User deleted", "info")
    else:    
        flash ("Pass deleted", "info")
    return redirect(url_for("get_passes", building_id=building_id))

@app.route("/passes/<int:user_id>/cust_portal", methods=["GET"])
def customer_pass_get(user_id):
    
    # Permit/deny access to page depening on logged in user
    if current_user.id == user_id or current_user.privilege == "superuser":
        pass
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    
    """ List of passes for a user """
    passes = session.query(Pass).filter(Pass.resident_id == user_id).all()
    
    plate_datetime(passes)
    
    # find building details
    building_id = session.query(User).filter(User.id == user_id).first().building_id
    building = session.query(Building).filter(Building.id == building_id).first()
    
    return render_template("cust_portal.html",
    passes=passes,
    building=building
    )
    
@app.route("/passes/<int:pass_id>/cust_use_pass", methods=["GET"])
def customer_use_pass_get(pass_id):
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
    # Permit/deny access to page depening on logged in user
    if current_user.id == pass_data.resident_id or current_user.privilege == "superuser":
        pass
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    
    return render_template("cust_use_pass.html",
    pass_data=pass_data,
    pass_user_id=pass_user_id
    )
    
@app.route("/passes/<int:pass_id>/cust_use_pass", methods=["POST"])
def customer_use_pass_post(pass_id):
    
    #Function for sending emails when a pass is in use
    def email_use_pass_func(email_dest):
        email_use_pass(building_name, user_name, pass_unit, pass_num, pass_license_plate, pass_plate_expire, email_dest)
        field_update = "Pass_num = {}, License_Plate = {}, Expiry Time = {}, Email_Dest = {}".format(pass_num, pass_license_plate, pass_plate_expire, email_dest)
        logger.debug("{}:uid {}:{}{}".format(building_name, current_user.id, "email trigger - ", field_update))



    building_id = session.query(Pass).filter_by(id=pass_id).first().building_id
    building_data = session.query(Building).filter_by(id=building_id).first()
    building_name = building_data.name
    building_timezone = building_data.timezone
    # Check if license plate has already been entered
    try:
        session.query(Pass).filter(Pass.license_plate.like(request.form["license_plate"])).first().license_plate
        flash ("License plate {} already in use, please use different license plate".format(request.form["license_plate"]), "warning")
        return redirect(url_for("customer_use_pass_get", pass_id=pass_id))
    except AttributeError:
        pass
    
    # update license plate and license plate expiry
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    pass_unit = pass_data.unit
    pass_num = pass_data.pass_id
    pass_data.license_plate = request.form["license_plate"]
    pass_license_plate = pass_data.license_plate
    pass_data.plate_expire = datetime.datetime.now() + datetime.timedelta(minutes = pass_data.maxtime)
    pass_plate_expire = dateformat(pass_data.plate_expire, building_timezone)

    # Get user info for this pass too
    user_data = session.query(User).filter(User.id == pass_data.resident_id).first()
    user_name = user_data.name
    email_dest = user_data.email

    # if email address(es) are filled in, then submit to DB also
    email1 = request.form["email1"]
    email2 = request.form["email2"]
    
    if len(email1) > 0:
        pass_data.email_1 = email1
        email_use_pass_func(email1)
    if len(email2) > 0:
        pass_data.email_2 = email2
        email_use_pass_func(email2)
    session.add(pass_data)
    
    db_commit_check(building_id,current_user.id,"UsePass PassID = {}, Pass = {}, License Plate = {}, Plate Expire = {} UTC, Email1 = {}, Email2 = {}".format
    (pass_id, pass_data.pass_id, pass_data.license_plate, pass_data.plate_expire, email1, email2))
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    flash ("Parking pass in effect", "success")

    email_use_pass_func(email_dest)

    return redirect(url_for("customer_pass_get", user_id=pass_user_id))
    
@app.route("/passes/<int:pass_id>/cust_end_pass", methods=["GET"])
def customer_end_pass_get(pass_id):
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
    # Permit/deny access to page depening on logged in user
    if current_user.id == pass_data.resident_id or current_user.privilege == "superuser":
        pass
    else:
        flash ("Authorization Error - redirected to login page", "danger")
        return redirect(url_for("login_get"))
    
    # Get info about this pass' user and building
    pass_user_id = pass_data.resident_id
    pass_building_id = pass_data.building_id
    building = session.query(Building).filter(Building.id == pass_building_id).first()
    
    return render_template("cust_end_pass.html",
    pass_data=pass_data,
    pass_user_id=pass_user_id,
    building=building
    )
    
@app.route("/passes/<int:pass_id>/cust_end_pass", methods=["POST"])
def customer_end_pass_post(pass_id):
    
    def email_end_pass_func(email_dest):
        email_end_pass(building_name, user_name, pass_unit, pass_num, pass_license_plate, pass_plate_expire, email_dest)

    building_id = session.query(Pass).filter_by(id=pass_id).first().building_id
    building_data = session.query(Building).filter_by(id=building_id).first()
    building_name = building_data.name
    building_timezone = building_data.timezone
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    pass_unit = pass_data.unit
    pass_num = pass_data.pass_id
    pass_license_plate = pass_data.license_plate

    curr_time=datetime.datetime.now()
    pass_plate_expire = dateformat(curr_time, building_timezone) + " - owner/tenant has ended pass"
    # Get user info for this pass too
    user_data = session.query(User).filter(User.id == pass_data.resident_id).first()
    user_name = user_data.name
    email_dest = user_data.email


    # send email out before resetting values
    email1 = pass_data.email_1
    email2 = pass_data.email_2
    
    if not email1 is None:
        email_end_pass_func(email1)
    if not email2 is None:
        email_end_pass_func(email2)


    # remove pass entries
    pass_data.license_plate = None
    pass_data.plate_expire = None
    pass_data.email_1 = None
    pass_data.email_2 = None
    session.add(pass_data)

    db_commit_check(building_id,current_user.id,"EndPass PassID = {}, Pass = {}, License Plate = {}, Plate Expire = {}".format(pass_id, pass_data.pass_id, pass_data.license_plate, pass_data.plate_expire))
    
    user_id = pass_data.resident_id
    
    flash ("Parking ended", "info")
    email_end_pass_func(email_dest)
    return redirect(url_for("customer_pass_get", user_id=user_id))

@app.route("/account_settings", methods=["GET"])
@login_required
def account_settings_get():
    user = session.query(User).filter_by(id=current_user.id).first()
    return render_template("account_settings.html", 
    user=user
    )
    
@app.route("/account_settings", methods=["POST"])
def account_settings_post():
    building_id = session.query(User).filter_by(id=current_user.id).first().building_id
    
    if request.form["action"] == "change_pswd":
        user = session.query(User).filter_by(id=current_user.id).first()
        curr_pswd = request.form["curr_pswd"]
        new_pswd = request.form["new_pswd"]
        confirm_pswd = request.form["confirm_pswd"]
    
        if not user or not check_password_hash(user.password, curr_pswd):
            flash("Incorrect username or password", "danger")
            return redirect(url_for("account_settings_get"))
        elif new_pswd != confirm_pswd:
            flash("New password and confirmation password do not match", "warning")
            return redirect(url_for("account_settings_get"))
        elif len(new_pswd) < 8:
            flash("Please use 8 or more characters for password", "warning")
            return redirect(url_for("account_settings_get"))
    
        user.password = generate_password_hash(new_pswd)
        session.add(user)
        db_commit_check(building_id,current_user.id,"Change UserID = {}, Email = {}, Password = {}".format(current_user.id, user.email, user.password))
        flash("Password has been changed successfully", "success")
        return redirect(url_for("logout_get"))
        
    elif request.form["action"] == "change_phone":
        user = session.query(User).filter_by(id=current_user.id).first()
        new_phone = request.form["phone"]
        user.phone = new_phone
        session.add(user)
        db_commit_check(building_id,current_user.id,"Change UserID = {}, Email = {}, Phone = {}".format(current_user.id, user.email, new_phone))
        flash("Phone number has been changed successfully", "success")
        return redirect(url_for("account_settings_get"))
            
    elif request.form["action"] == "change_email": 
        user = session.query(User).filter_by(id=current_user.id).first()
        new_email = request.form["email"]
        new_confirm_email = request.form["confirm_email"]
        
        if new_email != new_confirm_email:
            flash("New email and confirmation email do not match", "warning")
            return redirect(url_for("account_settings_get"))
        elif new_email == user.email:
            flash("newly entered email is the same as previous email", "warning")
            return redirect(url_for("account_settings_get"))
        
        try:
            session.query(User).filter(User.email.like(request.form["email"])).first().email
            flash("Email address already in use, you must use an unused email address", "danger")
            return redirect(url_for("account_settings_get"))
        except AttributeError:
            user.email = new_email
            session.add(user)
            db_commit_check(building_id,current_user.id,"Change UserID = {}, Email = {}".format(current_user.id, user.email))
            flash("Email address has been changed successfully", "success")
            flash("New username: {}".format(request.form["email"]), "success")
            return redirect(url_for("logout_get"))

@app.route("/forgot_password", methods=["GET"])
def forgot_password_get():
    return render_template("forgot_password.html")

@app.route("/forgot_password", methods=["POST"])
def forgot_password_post():

    email = request.form["email"]
    name = request.form["name"]
    phone = request.form["phone"]

    try:
        session.query(User).filter(User.email.like(email)).first().email
        user_data=session.query(User).filter(User.email.like(email)).first()

        if user_data.phone == phone:
            pass
        elif user_data.name == name:
            pass
        else:
            flash ("Incorrect verification details", "danger")
            return render_template("forgot_password.html")

        building_id=user_data.building_id
        user_id=user_data.id
        user_name=user_data.name
        user_phone=user_data.phone
        user_email=user_data.email

        building_name=session.query(Building).filter(Building.id == building_id).first().name

        #the remainder will only be done if "forget password" verification is correct
        print(user_data.email, user_data.phone, user_data.name, user_data.phone, user_data.password)
        password = []
        password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
        user_data.password = generate_password_hash(password)
        session.add(user_data)
        db_commit_check(building_id,"pwd_rst","Password Reset UserID= {}, Name = {}, Email = {}, Phone = {}, Pswd = {}".format(user_id,user_name,user_email,user_phone,password))
        
        email_subject = "VPass Portal - Password Update"
        email_address_add(building_name, user_name, email, password, email_subject)
        flash ("Temporary password has been emailed to {}".format(email), "success")
        return render_template("login.html")

    except AttributeError:
            flash ("No email found", "danger")
            return render_template("forgot_password.html")




@app.route("/login", methods=["GET"])
def login_get():
    return render_template("login.html")
    
@app.route("/login", methods=["POST"])
def login_post():
    email = request.form["email"]
    password = request.form["password"]
    user = session.query(User).filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        flash("Incorrect username or password (note: case sensitive)", "danger")
        return redirect(url_for("login_get"))
        
    login_user(user)
    if user.privilege in ("admin", "read_only"):
        return redirect(url_for("get_passes", building_id=user.building_id))
    elif user.privilege in ("general"):
        return redirect(url_for("customer_pass_get", user_id=user.id))
        
@app.route("/logout", methods=['GET'])
def logout_get():
    logout_user()
    return redirect(url_for("login_get"))