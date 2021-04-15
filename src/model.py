from peewee import *
from os import environ
from slugify import slugify

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
    db.create_tables([User, Album])
    disconnect()


class User(Model):
    name = CharField(unique=True)
    email = CharField()

    class Meta:
        database = db


class Album(Model):
    name = CharField(unique=True)
    slug = CharField(unique=True)

    class Meta:
        database = db

    def __init__(self, *args, **kwargs):
        if not 'slug' in kwargs:
            kwargs['slug'] = slugify(kwargs.get('name'))
        super().__init__(*args, **kwargs)

    def asdict(self):
        return {"slug": self.slug, "name": self.name}
