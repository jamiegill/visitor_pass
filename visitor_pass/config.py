import os
class DevelopmentConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://ubuntu:thinkful@localhost:5432/visitor_pass"
    DEBUG = True
    SECRET_KEY = os.environ.get("VISITOR_PASS_SECRET_KEY", os.urandom(12))
    SMTP_ADDRESS = "pickwheat@gmail.com"
    SMTP_PASSWORD = "gmail123@"
    SMTP_SERVER = "smtp.gmail.com:587"
    
class TestingConfig(object):
    SQLALCHEMY_DATABASE_URI = "postgresql://ubuntu:thinkful@localhost:5432/visitor_pass-test"
    DEBUG = True
    SECRET_KEY = "Not secret"
