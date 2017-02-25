import os
class DevelopmentConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://ubuntu:thinkful@localhost:5432/visitor_pass"
    DEBUG = True
    SECRET_KEY = os.environ.get("VISITOR_PASS_SECRET_KEY", os.urandom(12))
    
class TestingConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://ubuntu:thinkful@localhost:5432/visitor_pass-test"
    DEBUG = True
    SECRET_KEY = "Not secret"
