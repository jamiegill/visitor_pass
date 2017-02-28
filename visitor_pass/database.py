from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, ForeignKey
from flask_login import UserMixin
import datetime

from . import app

engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Building(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    address = Column(String(1024))
    contact_name = Column(String(128))
    contact_phone = Column(String(128))
    total_licenses = Column(Integer, nullable=False)
    used_licenses = Column(Integer)
    creation_date = Column(DateTime, default=datetime.datetime.now())
    
    visitor_pass = relationship("Pass", backref="building")
    privilege_user = relationship("User", backref="building")
    
class Pass(Base):
    __tablename__ = "passes"
    id = Column(Integer, primary_key=True)
    pass_id = Column(String(128), nullable=False)
    maxtime = Column(Integer, nullable=False)
    license_plate = Column(String(128), unique=True)
    plate_expire = Column(DateTime)
    email_1 = Column(String(1024))
    email_2 = Column(String(1024))
    creation_date = Column(DateTime, default=datetime.datetime.now())
    
    building_id = Column(Integer, ForeignKey('buildings.id'), nullable=False)
    resident_id = Column(Integer, ForeignKey('users.id'))

    
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    email = Column(String(1024), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    privilege = Column(String(128))

    visitor_pass = relationship("Pass", backref="resident")
    building_id = Column(Integer, ForeignKey('buildings.id'))
    
    
Base.metadata.create_all(engine)