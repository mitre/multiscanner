from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import sys
import os
import time

# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CWD))
import multiscanner


def dummy(a, b):
    return a * b


def test_thread_return():
    t = multiscanner._Thread(target=dummy, args=(2, 3))
    t.start()
    t.join()
    assert t.ret == 6


def test_thread_started():
    t = multiscanner._Thread(target=dummy, args=(2, 3))
    assert not t.started
    t.start()
    time.sleep(.001)
    assert t.started
    t.join()


def test_thread_times():
    t = multiscanner._Thread(target=time.sleep, args=(.1,))
    t.start()
    t.join()
    assert t.starttime < t.endtime
    assert (t.starttime - t.endtime) < 1
