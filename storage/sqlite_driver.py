#!/usr/bin/env python
from __future__ import print_function
import os
import json
import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, ConcreteBase
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MS_WD, "storage.ini")

Base = declarative_base()


class Task(Base):
    __tablename__ = "Tasks"

    task_id = Column(Integer, primary_key=True)
    task_status = Column(String)
    report_id = Column(String, unique=False)

    def __repr__(self):
        return '<Task("{0}","{1}","{2}")>'.format(
            self.task_id, self.task_status, self.report_id
        )

    def to_dict(self):
        return {attr.name: getattr(self, attr.name) for attr in self.__table__.columns}

    def to_json(self):
        return json.dumps(self.to_dict())

class Database(object):
    '''
    This class enables CRUD operations with the database that holds the task definitions.
    Note that in the configuration file, the database type (parameter: db_type) needs to be
    a SQLAlchemy dialect: sqlite, mysql, postgresql, oracle, or mssql. The driver can optionally be
    specified as well, i.e., 'postgresql+psycopg2' (see http://docs.sqlalchemy.org/en/latest/core/engines.html).
    '''
    DEFAULTCONF = {
        'db_type': 'sqlite',
        'host_string': 'localhost',
        'db_name': 'task_db',
        'username': 'multiscanner',
        'password': 'changeme'
    }

    def __init__(self, config=None):
        self.config = config
        self.db_connection_string = None

    def _parse_config(self):
        '''
        Checks if a config was passed in. If no config was passed in,
        attempts to read the config from the storage.ini file. If the config is
        not defined there, uses the default config
        '''
        if not self.config:
            config_parser = ConfigParser.SafeConfigParser()
            config_parser.read(CONFIG_FILE)
            try:
                self.config = dict(config_parser.items(self.__class__.__name__))
            except ConfigParser.NoSectionError:
                self.config = self.DEFAULTCONF

    def _get_db_engine(self):
        return create_engine(self.db_connection_string)

    def init_db(self):
        self._parse_config()
        db_type = self.config['db_type']
        db_name = self.config['db_name']
        if db_type == 'sqlite':
            # we can ignore host, username, password, etc
            sql_lite_db_path = os.path.join(MS_WD, db_name)
            self.db_connection_string = 'sqlite:///{}'.format(sql_lite_db_path)
        else:
            username = self.config['username']
            password = self.config['password']
            host_string = self.config['host_string']
            self.db_connection_string = '{}://{}:{}@{}/{}'.format(db_type, username, password, host_string, db_name)

        print(self.db_connection_string)
        eng = self._get_db_engine()
        Base.metadata.bind = eng
        Base.metadata.create_all()

    def init_sqlite_db(self):
        global Base
        eng = create_engine('sqlite:///%s' % self.db_path)
        Base.metadata.bind = eng
        Base.metadata.create_all()


    def add_task(self, task_id=None, task_status='Pending', report_id=None):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = Task(
            task_id=task_id,
            task_status='Pending',
            report_id=None
        )
        try:
            ses.add(task)
            ses.commit()
        except IntegrityError as e:
            print('PRIMARY KEY must be unique! %s' % e)
            return -1
        return task.task_id


    def update_task(self, task_id, task_status, report_id=None):
        '''
        report_id will be a list of sha values
        '''
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = ses.query(Task).get(task_id)
        if task:
            task.task_status = task_status
            task.report_id = report_id
            ses.commit()
            return task.to_dict()

    def get_task(self, task_id):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = ses.query(Task).get(task_id)
        if task:
            return task

    def get_report_id_from_task(self, task_id):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = ses.query(Task).get(task_id)
        if task:
            return task.report_id

    def get_all_tasks(self):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()
        rs = ses.query(Task).all()

        # For testing, do not use in production
        task_list = []
        for task in rs:
            task_list.append(task.to_dict())
        return task_list

    def delete_task(self, task_id):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = ses.query(Task).get(task_id)
        if task:
            ses.delete(task)
            ses.commit()
            return True
        else:
            return False
