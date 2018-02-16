# -*- coding: utf-8 -*-
import sys
import os
# Makes sure we use the multiscanner in ../
CWD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(CWD))
import multiscanner

def test_valid_reports_string():
    reportlist = [([('file', 'result')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=False)
    assert r == '{"file":{"Test":"result"}}'

def test_valid_reports_python():
    reportlist = [([('file', 'result')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=True)
    assert r == {"file": {"Test": "result"}}

def test_valid_utf8_string():
    reportlist = [([('file', '안녕하세요')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=False)
    assert r == u'{"file":{"Test":"안녕하세요"}}'

def test_valid_utf8_python():
    reportlist = [([('file', '안녕하세요')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=True)
    assert r == {"file": {"Test": "안녕하세요"}}

def test_invalid_utf8_string():
    reportlist = [([('file', '\x97안녕하세요')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=False)
    assert r == u'{"file":{"Test":"\x97안녕하세요"}}' or r == u'{"file":{"Test":"\ufffd안녕하세요"}}'

def test_invalid_utf8_python():
    reportlist = [([('file', '\x97안녕하세요')], {'Name': 'Test', 'Type': 'Test'})]
    r = multiscanner.parse_reports(reportlist, python=True)
    assert r == {"file": {"Test": "\x97안녕하세요"}} or r == {"file": {"Test": u"\ufffd안녕하세요"}}
