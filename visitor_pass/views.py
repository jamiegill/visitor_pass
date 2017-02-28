from flask import render_template, request, redirect, url_for, flash
#from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash
import datetime
from . import app
from .database import session, Pass, Building, User

@app.route("/")
@app.route("/passes/<int:building_id>")
def get_passes(building_id):
    """ List of passes for a building """
    
    passes = session.query(Pass)
    passes = passes.order_by(Pass.id.desc())
    passes = passes.filter(Pass.building_id == building_id)
    
    # find building details
    building = session.query(Building).filter(Building.id == building_id).first()
    
    return render_template("view_passes.html",
    passes=passes,
    building=building
    )
    
#@app.route("/passes/edit/<int:id>", methods=["GET"])
#def edit_passes(id):
#    """ view edit page """
#    
#    passes = session.query(Pass).filter(Pass.id == id).first()
#    return render_template("edit_pass.html",
#    passes=passes
#    )

@app.route("/passes/<int:building_id>/add", methods=["GET"])
def add_pass_get(building_id):
    building = session.query(Building)
    building = building.filter(Building.id == building_id).first()
    return render_template("add_pass.html",
    building=building
    )
    
@app.route("/passes/<int:building_id>/add", methods=["POST"])
def add_pass_post(building_id):
    # Add email address to the DB
    add_email = User(
        email=request.form["email"],
        name=request.form["name"],
        password="test",
        building_id=building_id
    )
    session.add(add_email)
    session.commit()
    
    # Once email is added to DB, get the last "added userid" and use this for next DB addition
    added_userid=session.query(User.id).order_by(User.id.desc()).first()[0]
    
    # Add a pass to the DB 
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
    
    # increase licenses used counter
    
    
    
    return redirect(url_for("get_passes", building_id=building_id))

#@app.route("/passes/cust_portal")
#def customer_edit():
#    
#    passes = session.query(Pass)
#    passes = passes.order_by(Pass.id.desc())
#    
#    return render_template("cust_portal",
#    passes = passes)
    
