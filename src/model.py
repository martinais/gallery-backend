import os
from peewee import *
from slugify import slugify

BASE_PATH = "/srv/data/"

db = PostgresqlDatabase(
    os.environ.get('DB_NAME'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASS'),
    host=os.environ.get('DB_HOST')
)


def connect():
    #if not db.connect(reuse_if_open=True): # TODO: find where the db keep being opened
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

    def exists(self):
        return User.find(self.name).count() > 0

    def find(name):
        return User.select().where(User.name == name)

    def asdict(self):
        return {"name": self.name, "email": self.email}


class Album(Model):
    path = os.path.join(BASE_PATH, "albums")
    name = CharField(unique=True)
    slug = CharField(unique=True)
    pics = []

    class Meta:
        database = db

    def __init__(self, *args, **kwargs):
        if not 'slug' in kwargs:
            kwargs['slug'] = slugify(kwargs.get('name'))
        self.path = os.path.join(self.path, kwargs['slug'])
        try:
            os.mkdir(self.path)
        except FileExistsError:
            with os.scandir(self.path) as files:
                self.pics = [f.name for f in files]
        super().__init__(*args, **kwargs)

    def exists(self):
        return Album.find(self.name).count() > 0

    def find(name):
        return Album.select().where(Album.name == name)

    def asdict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "count": len(self.pics),
            "preview": None if len(self.pics) == 0 else self.pics[0]
        }

    def add_pics(self, pics):
        for filehash in pics:
            album_path = os.path.join(self.path, filehash)
            pic_path = os.path.join(BASE_PATH, 'pics', filehash)
            if os.path.exists(pic_path) and not os.path.exists(album_path):
                os.symlink(pic_path, album_path)

    def remove_pics(self, pics):
        for filehash in pics:
            album_path = os.path.join(self.path, filehash)
            if os.path.exists(album_path):
                os.remove(album_path)

    def xremove(self, debug):
        self.remove_pics(self.pics)
        os.rmdir(self.path)
        return self.delete_instance()
