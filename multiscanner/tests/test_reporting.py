from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import multiscanner


def test_none_report():
    test_results = [([('a', True), ('b', '/tmp/b'), ('c', True), ('/d/d', '/tmp/d')], {'Name': 'test_2', 'Include': True, 'Type': 'Test'}), None]   # noqa: E501
    report = multiscanner.parse_reports(test_results, ugly=True, includeMetadata=False, python=False)
    assert report == '{"/d/d":{"test_2":"/tmp/d"},"a":{"test_2":true},"b":{"test_2":"/tmp/b"},"c":{"test_2":true}}'


def test_empty_report():
    test_results = [([('a', True), ('b', '/tmp/b'), ('c', True), ('/d/d', '/tmp/d')], {'Name': 'test_2', 'Include': True, 'Type': 'Test'}), ([], {})]   # noqa: E501
    report = multiscanner.parse_reports(test_results, ugly=True, includeMetadata=False, python=False)
    assert report == '{"/d/d":{"test_2":"/tmp/d"},"a":{"test_2":true},"b":{"test_2":"/tmp/b"},"c":{"test_2":true}}'


def test_meta_report():
    test_results = [([('a', True), ('b', '/tmp/b'), ('c', True), ('/d/d', '/tmp/d')], {'Name': 'test_2', 'Include': True, 'Type': 'Test', 'Var': 1})]   # noqa: E501
    report = multiscanner.parse_reports(test_results, ugly=True, includeMetadata=True, python=False)
    assert report == '{"Files":{"/d/d":{"test_2":"/tmp/d"},"a":{"test_2":true},"b":{"test_2":"/tmp/b"},"c":{"test_2":true}},"Metadata":{"test_2":{"Include":true,"Name":"test_2","Type":"Test","Var":1}}}'  # noqa: E501
