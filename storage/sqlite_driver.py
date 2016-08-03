#!/usr/bin/env python
from __future__ import print_function
import os
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, ConcreteBase
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = 'sqlite.db'
FULL_DB_PATH = os.path.join(MS_WD, DB_NAME)


Base = declarative_base()


class Task(Base):
    __tablename__ = "Tasks"

    task_id = Column(Integer, primary_key=True)
    task_status = Column(String)
    report_id = Column(Integer, unique=False)

    def __repr__(self):
        return '<Task("{0}","{1}","{2}")>'.format(
            self.task_id, self.task_status, self.report_id
        )

    def to_dict(self):
        return {attr.name: getattr(self, attr.name) for attr in self.__table__.columns}

    def to_json(self):
        return json.dumps(self.to_dict())

class Database(object):
    def __init__(self, db_path=FULL_DB_PATH):
        self.db_path = db_path

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
            task.report_id = repr(report_id)
            ses.commit()
            return task.to_dict()

    def get_task(self, task_id):
        eng = create_engine('sqlite:///%s' % self.db_path)
        Session = sessionmaker(bind=eng)
        ses = Session()

        task = ses.query(Task).get(task_id)
        if task:
            return task.to_dict()

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


def main():
    db = Database()
    db.init_sqlite_db()

    task_id = db.add_task()
    print(db.get_task(task_id))
    report_id = ['815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66', '4aa3d6a17af264d26536b5551e58af4c2c2a13d40b47ac52d782911ec76612a8']
    db.update_task(task_id=task_id, task_status='Complete', report_id=report_id)
    print(db.get_task(task_id))
    print(db.delete_task(33))

    for task in db.get_all_tasks():
        print(task)


if __name__ == '__main__':
    main()
