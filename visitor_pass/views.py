from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user, logout_user
from .login import load_user
import datetime
from . import app
from .database import session, Pass, Building, User
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

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
            session.add(pass_record)
            session.commit()

@app.route("/")
@app.route("/passes/<int:building_id>")
@login_required
def get_passes(building_id):
    """ List of passes for a building """
    
    if current_user.privilege in ("admin", "superuser") and current_user.building_id == building_id:
        access_priv = "admin"
    elif current_user.privilege in ("read_only") and current_user.building_id == building_id:
        access_priv = "read_only"
    else:
        flash ("Authorization Error - redirected to login page")
        return redirect(url_for("login_get"))
    
    passes = session.query(Pass)
    passes = passes.order_by(Pass.plate_expire.asc())
    passes = passes.filter(Pass.building_id == building_id)
    
    # find building details
    building = session.query(Building).filter(Building.id == building_id).first()
    
    plate_datetime(passes)
    return render_template("view_passes.html",
    passes=passes,
    building=building,
    access_priv=access_priv
    )

@app.route("/passes/<int:building_id>/add", methods=["GET"])
def add_pass_get(building_id):
    building = session.query(Building)
    building = building.filter(Building.id == building_id).first()
    total_licenses = building.total_licenses
    used_licenses = building.used_licenses
    if used_licenses >= total_licenses:
        flash ("Max licenses used. Please delete users or purchase more licenses")
        return redirect(url_for("get_passes", building_id=building_id))
            
    return render_template("add_pass.html",
    building=building
    )
    
@app.route("/passes/<int:building_id>/add", methods=["POST"])
def add_pass_post(building_id):
    # Check for duplicate pass_id
    try:
        building=session.query(Pass).filter(Pass.building_id == building_id)
        building.filter(Pass.pass_id.like(request.form["pass_id"])).first().pass_id
        flash ("Pass \"{}\" has already been added, please add a new pass".format(request.form["pass_id"]))
        return redirect(url_for("add_pass_get", building_id=building_id))
    except AttributeError:
        pass
    
    
    # Check for duplicate email
    try:
        session.query(User).filter(User.email.like(request.form["email"])).first().email
        flash ("Adding pass to existing email: {}".format(request.form["email"]))
        
    except AttributeError:
        # Add email address to the DB
        password = []
        password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
        add_email = User(
        email=request.form["email"],
        name=request.form["name"],
        privilege="general",
        password=generate_password_hash(password),
        building_id=building_id
        )
        session.add(add_email)
        session.commit()
    
    
    
    # Once email is added to DB, get the last "added userid" and use this for next DB addition
    added_userid=session.query(User.id).order_by(User.id.desc()).first()[0]
    
    # Add a pass to the DB and increase licenses used counter 
    add_pass = Pass(
        pass_id=request.form["pass_id"],
        maxtime=request.form["maxtime"],
        building_id=building_id,
        resident_id=added_userid
    )
    building = session.query(Building).filter(Building.id == building_id).first()
    building.used_licenses = building.used_licenses + 1
    session.add_all([add_pass, building])
    session.commit()
    flash ("Pass added and user added - please record credentials below and supply them to the resident".format(request.form["email"],password))
    flash ("Username: {}".format(request.form["email"]))
    flash ("Password: {}".format(password))
    return redirect(url_for("get_passes", building_id=building_id))

@app.route("/passes/<int:pass_id>/delete", methods=["GET"])
def delete_pass_get(pass_id):
    delete_email = []
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
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
    """ Delete Pass, decrease license count, Delete User """
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
    building.used_licenses = building.used_licenses - 1
        
    session.add(building)
    session.commit()
    
    
    # Delete the user if only 1 instance is found in the passes DB
    user_instances = len(session.query(Pass).filter(Pass.resident_id == pass_user_id).all())
    if user_instances == 0:
        user_data = session.query(User).filter(User.id == pass_user_id).first()
        session.delete(user_data)
        session.commit()
        flash ("Pass and User deleted")
    else:    
        flash ("Pass deleted")
    return redirect(url_for("get_passes", building_id=building_id))

@app.route("/passes/<int:user_id>/cust_portal", methods=["GET"])
def customer_pass_get(user_id):
    
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
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    
    return render_template("cust_use_pass.html",
    pass_data=pass_data,
    pass_user_id=pass_user_id
    )
    
@app.route("/passes/<int:pass_id>/cust_use_pass", methods=["POST"])
def customer_use_pass_post(pass_id):
    # Check if license plate has already been entered
    try:
        session.query(Pass).filter(Pass.license_plate.like(request.form["license_plate"])).first().license_plate
        flash ("License plate {} already in use, please use different license plate".format(request.form["license_plate"]))
        return redirect(url_for("customer_use_pass_get", pass_id=pass_id))
    except AttributeError:
        pass
    
    # update license plate and license plate expiry
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    pass_data.license_plate = request.form["license_plate"]
    pass_data.plate_expire = datetime.datetime.now() + datetime.timedelta(minutes = pass_data.maxtime)
    session.add(pass_data)
    session.commit()
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    flash ("Parking pass in effect")
    return redirect(url_for("customer_pass_get", user_id=pass_user_id))
    
@app.route("/passes/<int:pass_id>/cust_end_pass", methods=["GET"])
def customer_end_pass_get(pass_id):
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    
    # Get info about this pass' user
    pass_user_id = pass_data.resident_id
    
    return render_template("cust_end_pass.html",
    pass_data=pass_data,
    pass_user_id=pass_user_id
    )
    
@app.route("/passes/<int:pass_id>/cust_end_pass", methods=["POST"])
def customer_end_pass_post(pass_id):
    # Get info about this pass
    pass_data = session.query(Pass).filter(Pass.id == pass_id).first()
    pass_data.license_plate = None
    pass_data.plate_expire = None
    session.add(pass_data)
    session.commit()
    
    user_id = pass_data.resident_id
    
    flash ("Parking ended")
    return redirect(url_for("customer_pass_get", user_id=user_id))


@app.route("/login", methods=["GET"])
def login_get():
    return render_template("login.html")
    
@app.route("/login", methods=["POST"])
def login_post():
    email = request.form["email"]
    password = request.form["password"]
    user = session.query(User).filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        flash("Incorrect username or password")
        return redirect(url_for("login_get"))
        
    login_user(user)
    if user.privilege in ("admin", "read_only"):
        return redirect(url_for("get_passes", building_id=user.building_id))
    elif user.privilege in ("general"):
        return redirect(url_for("customer_pass_get", user_id=user.id))