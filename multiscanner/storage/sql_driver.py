#!/usr/bin/env python
from __future__ import print_function

import codecs
import configparser
import json
import os
from contextlib import contextmanager
from datetime import datetime

from datatables import ColumnDT, DataTables
from sqlalchemy import (Column, DateTime, Integer, String, and_, create_engine,
                        func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import aliased, sessionmaker
from sqlalchemy_utils import create_database, database_exists

from multiscanner import CONFIG


CONFIG_FILE = os.path.join(os.path.split(CONFIG)[0], "api_config.ini")

Base = declarative_base()
Session = sessionmaker()


class Task(Base):
    __tablename__ = "Tasks"

    task_id = Column(Integer, primary_key=True)
    task_status = Column(String)
    sample_id = Column(String, unique=False)
    timestamp = Column(DateTime)

    def __repr__(self):
        return '<Task("{0}","{1}","{2}","{3}")>'.format(
            self.task_id, self.task_status, self.sample_id, self.timestamp
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
        'password': 'CHANGEME',
        'retry_time': 5,  # Number of seconds to wait between retrying to connect to task database
        'retry_num': 20,  # Number of times to retry to connect to task database
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
            sql_lite_db_path = os.path.join(os.path.split(CONFIG)[0], db_name)
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
        except Exception as e:
            # TODO: log exception
            ses.rollback()
            raise
        finally:
            ses.close()

    def add_task(self, task_id=None, task_status='Pending', sample_id=None, timestamp=None):
        with self.db_session_scope() as ses:
            task = Task(
                task_id=task_id,
                task_status=task_status,
                sample_id=sample_id,
                timestamp=timestamp,
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

    def update_task(self, task_id, task_status, timestamp=None):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                task.task_status = task_status
                if timestamp:
                    task.timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')
                return task.to_dict()

    def get_task(self, task_id):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                # unbind Task from Session
                ses.expunge(task)
                return task

    def get_all_tasks(self):
        with self.db_session_scope() as ses:
            rs = ses.query(Task).all()
            # TODO: For testing, do not use in production
            task_list = []
            for task in rs:
                ses.expunge(task)
                task_list.append(task.to_dict())
            return task_list

    def search(self, params, id_list=None, search_by_value=False, return_all=False):
        '''Search according to Datatables-supplied parameters.
        Returns results in format expected by Datatables.
        '''
        with self.db_session_scope() as ses:
            fields = [Task.task_id, Task.sample_id, Task.task_status, Task.timestamp]
            columns = [ColumnDT(f) for f in fields]
            if return_all:
                # History page
                if id_list is None:
                    # Return all tasks
                    query = ses.query(*fields)
                else:
                    # Query all tasks for samples with given IDs
                    query = ses.query(*fields).filter(Task.sample_id.in_(id_list))
            else:
                # Analyses page
                task_alias = aliased(Task)
                sample_subq = (ses.query(task_alias.sample_id,
                                         func.max(task_alias.timestamp).label('ts_max'))
                               .group_by(task_alias.sample_id)
                               .subquery()
                               .alias('sample_subq'))
                # Query for most recent task per sample
                query = (ses.query(*fields)
                         .join(sample_subq,
                               and_(Task.sample_id == sample_subq.c.sample_id,
                                    Task.timestamp == sample_subq.c.ts_max)))
                if id_list is not None:
                    # Query for most recent task per sample, only for samples with given IDs
                    query = query.filter(Task.sample_id.in_(id_list))
            if not search_by_value:
                # Don't limit search by search term or it won't return anything
                # (search term already handled by Elasticsearch)
                del params['search[value]']
            rowTable = DataTables(params, query, columns)

            output = rowTable.output_result()
            ses.expunge_all()

            return output

    def delete_task(self, task_id):
        with self.db_session_scope() as ses:
            task = ses.query(Task).get(task_id)
            if task:
                ses.delete(task)
                return True
            else:
                return False

    def exists(self, sample_id):
        '''Checks if any tasks exist in the database with the given sample_id.

        Returns:
            Task id of the most recent task with the given sample_id if one
            exists in task database, otherwise None.
        '''
        with self.db_session_scope() as ses:
            # Query for most recent task with given sample_id
            subquery = (ses.query(func.max(Task.timestamp))
                .filter(Task.sample_id == sample_id))
            task = ses.query(Task).filter(Task.sample_id == sample_id,
                                          Task.timestamp == subquery).first()

            if task:
                return task.task_id
            else:
                return None
