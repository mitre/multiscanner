#!/usr/bin/env python

import os

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


def init_sqlite_db():
    global Base
    eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
    Base.metadata.bind = eng
    Base.metadata.create_all()


def add_record(task_id=None, task_status='Pending', report_id=None):
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


def update_record(task_id, task_status, report_id=None):
    eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
    Session = sessionmaker(bind=eng)
    ses = Session()

    record = ses.query(Record).get(task_id)
    if record:
        record.task_status = task_status
        record.report_id = report_id
        ses.commit()
        return record

def print_all_records():
    eng = create_engine('sqlite:///%s' % FULL_DB_PATH)
    Session = sessionmaker(bind=eng)
    ses = Session()
    rs = ses.query(Record).all()

    for record in rs:
           print record


def main():
    init_sqlite_db()

    task_id = add_record()
    update_record(task_id=task_id, task_status='Complete', report_id=task_id)

    print_all_records()


if __name__ == '__main__':
    main()
