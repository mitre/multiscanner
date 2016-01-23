from __future__ import division, absolute_import, print_function, unicode_literals
import sys
import os
# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CWD))
import multiscanner

sys.path.append(os.path.join(CWD, '..', 'libs'))
import common

def add_int(x, y):
    return x + y

def test_subscan():
    m = multiscanner.multiscan(['fake.zip'], recursive=None, configfile=None, module_list=[os.path.join(CWD, 'modules', 'test_subscan.py')])
    assert m == [([(u'fake.zip', 0)], {'Type': 'Test', 'Name': 'test_subscan'}), ([(u'fake.zip/0', u'fake.zip')], {u'Include': False, u'Type': u'subscan', u'Name': u'Parent'}), ([(u'fake.zip', [u'fake.zip/0'])], {u'Include': False, u'Type': u'subscan', u'Name': u'Children'}), ([(u'fake.zip/0', u'test_subscan')], {u'Include': False, u'Type': u'subscan', u'Name': u'Created by'}), ([(u'fake.zip/0', 1)], {'Type': 'Test', 'Name': 'test_subscan'}), ([(u'fake.zip/0/1', u'fake.zip/0')], {u'Include': False, u'Type': u'subscan', u'Name': u'Parent'}), ([(u'fake.zip/0', [u'fake.zip/0/1'])], {u'Include': False, u'Type': u'subscan', u'Name': u'Children'}), ([(u'fake.zip/0/1', u'test_subscan')], {u'Include': False, u'Type': u'subscan', u'Name': u'Created by'}), ([(u'fake.zip/0/1', 2)], {'Type': 'Test', 'Name': 'test_subscan'})]

def test_async_normal():
    gi = multiscanner._GlobalModuleInterface()
    mi = multiscanner._ModuleInterface('testing', gi)
    async_list = []
    for i in range(0, 10):
        async_list.append(mi.apply_async(add_int, (i, 1)))

    i = 1
    for a in async_list:
        assert i == a.get()
        i += 1
