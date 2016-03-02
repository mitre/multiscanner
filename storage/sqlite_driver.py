#!/usr/bin/env python

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


class Record(Base):
    __tablename__ = "Records"

    task_id = Column(Integer, primary_key=True)
    task_status = Column(String)
    report_id = Column(Integer, unique=True)

    def __repr__(self):
        return '<Task("{0}","{1}","{2}")>'.format(
            self.task_id, self.task_status, self.report_id
        )

    def to_dict(self):
        return {attr.name: getattr(self, attr.name) for attr in self.__table__.columns}

    def to_json(self):
        return json.dumps(self.to_dict())

class Database(object):
    def init_sqlite_db(self):
        global Base
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Base.metadata.bind = eng
        Base.metadata.create_all()


    def add_task(self, task_id=None, task_status='Pending', report_id=None):
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Session = sessionmaker(bind=eng)
        ses = Session()

        record = Record(
            task_id=task_id,
            task_status='Pending',
            report_id=None
        )
        try:
            ses.add(record)
            ses.commit()
        except IntegrityError as e:
            print 'PRIMARY KEY must be unique! %s' % e
            return -1
        return record.task_id


    def update_record(self, task_id, task_status, report_id=None):
        '''
        report_id will be a list of sha values
        '''
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Session = sessionmaker(bind=eng)
        ses = Session()

        record = ses.query(Record).get(task_id)
        if record:
            record.task_status = task_status
            record.report_id = repr(report_id)
            ses.commit()
            return record.to_dict()

    def get_task(self, task_id):
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Session = sessionmaker(bind=eng)
        ses = Session()

        record = ses.query(Record).get(task_id)
        if record:
            return record.to_dict()

    def get_all_tasks(self):
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Session = sessionmaker(bind=eng)
        ses = Session()
        rs = ses.query(Record).all()

        # For testing, do not use in production
        record_list = []
        for record in rs:
            record_list.append(record.to_dict())
        return record_list

    def delete_task(self, task_id):
        eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
        Session = sessionmaker(bind=eng)
        ses = Session()

        record = ses.query(Record).get(task_id)
        if record:
            ses.delete(record)
            ses.commit()
            return True
        else:
            return False


def main():
    db = Database()
    db.init_sqlite_db()

    task_id = db.add_task()
    print db.get_task(task_id)
    report_id = ['815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66', '4aa3d6a17af264d26536b5551e58af4c2c2a13d40b47ac52d782911ec76612a8']
    db.update_record(task_id=task_id, task_status='Complete', report_id=report_id)
    print db.get_task(task_id)
    print db.delete_task(33)

    for record in db.get_all_tasks():
        print record


if __name__ == '__main__':
    main()
