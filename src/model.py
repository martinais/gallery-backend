from peewee import *
from os import environ

db = PostgresqlDatabase(
    environ.get('DB_NAME'),
    user=environ.get('DB_USER'),
    password=environ.get('DB_PASS'),
    host=environ.get('DB_HOST')
)


def connect():
    if not db.connect():
        exit("ERROR: unable to connect to database")


def disconnect():
    db.close()


def migrate_database():
    connect()
    db.create_tables([User])
    disconnect()


class User(Model):
    name = CharField(unique=True)
    email = CharField()

    class Meta:
        database = db
