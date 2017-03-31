#!/usr/bin/env python
from __future__ import print_function
import os
import json
import configparser
import codecs
import sys
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, ConcreteBase
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy_utils import database_exists, create_database


MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(MS_WD, "api_config.ini")

if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.append(os.path.join(MS_WD, 'libs'))
import common

Base = declarative_base()
Session = sessionmaker()

class Task(Base):
    __tablename__ = "Tasks"

    task_id = Column(Integer, primary_key=True)
    task_status = Column(String)
    sample_id = Column(String, unique=False)
    report_id = Column(String, unique=False)

    def __repr__(self):
        return '<Task("{0}","{1}","{2}","{3}")>'.format(
            self.task_id, self.task_status, self.sample_id, self.report_id
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
        'password': 'CHANGEME'
    }

    def __init__(self, config=None, configfile=CONFIG_FILE, regenconfig=False):
        self.db_connection_string = None
        self.db_engine = None

        # Configuration parsing
        config_parser = configparser.SafeConfigParser()
        config_parser.optionxform = str

        # (re)generate conf file if necessary
        if regenconfig or not os.path.isfile(configfile):
            self._rewrite_config(config_parser, configfile, config)
        # now read in and parse the conf file
        config_parser.read(configfile)
        # If we didn't regen the config file in the above check, it's possible
        # that the file is missing our DB settings...
        if not config_parser.has_section(self.__class__.__name__):
            self._rewrite_config(config_parser, configfile, config)
            config_parser.read(configfile)

        # If configuration was specified, use what was stored in the config file
        # as a base and then override specific settings as contained in the user's
        # config. This allows the user to specify ONLY the config settings they want to
        # override
        config_from_file = dict(config_parser.items(self.__class__.__name__))
        if config:
            for key_ in config:
                config_from_file[key_] = config[key_]
        self.config = config_from_file

    def _rewrite_config(self, config_parser, configfile, usr_override_config):
        """
        Regenerates the Database-specific part of the API config file
        """
        if os.path.isfile(configfile):
            # Read in the old config
            config_parser.read(configfile)
        if not config_parser.has_section(self.__class__.__name__):
            config_parser.add_section(self.__class__.__name__)
        if not usr_override_config:
            usr_override_config = self.DEFAULTCONF
        # Update config
        for key_ in usr_override_config:
            config_parser.set(self.__class__.__name__, key_, str(usr_override_config[key_]))

        with codecs.open(configfile, 'w', 'utf-8') as conffile:
            config_parser.write(conffile)

    def init_db(self):
        """
        Initializes the database connection based on the configuration parameters
        """
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

        self.db_engine = create_engine(self.db_connection_string)
        # If db not present AND type is not SQLite, create the DB
        if not self.config['db_type'] == 'sqlite':
            if not database_exists(self.db_engine.url):
                create_database(self.db_engine.url)
        Base.metadata.bind = self.db_engine
        Base.metadata.create_all()
        # Bind the global Session to our DB engine
        global Session
        Session.configure(bind=self.db_engine)

    @contextmanager
    def db_session_scope(self):
        """
        Taken from http://docs.sqlalchemy.org/en/latest/orm/session_basics.html.
        Provides a transactional scope around a series of operations.
        """
        ses = Session()
        try:
            yield ses
            ses.commit()
        except:
            ses.rollback()
            raise
        finally:
            ses.close()

    def add_task(self, task_id=None, task_status='Pending', sample_id=None, report_id=None):
        with self.db_session_scope() as ses:
            task = Task(
                task_id=task_id,
                task_status=task_status,
                sample_id=sample_id,
                report_id=report_id
            )
            try:
                ses.add(task)
                # Need to explicitly commit here in order to update the ID in the DAO
                ses.commit()
            except IntegrityError as e:
                print('PRIMARY KEY must be unique! %s' % e)
                return -1
            created_task_id = task.task_id
            return created_task_id

    def update_task(self, task_id, task_status, report_id=None):
        '''
        report_id will be a list of sha values
        '''
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                task.task_status = task_status
                task.report_id = report_id
                return task.to_dict()

    def get_task(self, task_id):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                # unbind Task from Session
                ses.expunge(task)
                return task

    def get_report_id_from_task(self, task_id):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                return task.report_id

    def get_all_tasks(self):
        with self.db_session_scope() as ses:
            rs = ses.query(Task).all()
            # TODO: For testing, do not use in production
            task_list = []
            for task in rs:
                ses.expunge(task)
                task_list.append(task.to_dict())
            return task_list

    def delete_task(self, task_id):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                ses.delete(task)
                return True
            else:
                return False
