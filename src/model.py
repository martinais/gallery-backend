from peewee import *

db = PostgresqlDatabase(
    'gallery', user='postgres', password='postgres', host='database'
)


class User(Model):
    name = CharField(unique=True)
    email = CharField()

    class Meta:
        database = db


def migrate_database():
    connect()
    db.create_tables([User])
    disconnect()


def connect():
    if not db.connect():
        exit("ERROR: unable to connect to database")


def disconnect():
    db.close()
