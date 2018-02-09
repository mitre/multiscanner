import os
import sys
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'libs'))

import common

def test_list2cmdline():
    l = ['1', 'a', '"dsafsad"']
    result = '1 a "dsafsad"'
    assert common.list2cmdline(l) == result

def test_dirname_linux_file():
    linux_file = '/a/b/c/d.txt'
    result = common.dirname(linux_file)
    assert result == '/a/b/c'

def test_dirname_linux_path():
    linux_dir = '/a/b/c/d/'
    result = common.dirname(linux_dir)
    assert result == '/a/b/c/d'

def test_dirname_win_file():
    win_file = 'A:\\b\\c\\d.txt'
    result = common.dirname(win_file)
    assert result == 'A:\\b\\c'

def test_dirname_win_path():
    win_dir = 'A:\\b\\c\\d\\'
    result = common.dirname(win_dir)
    assert result == 'A:\\b\\c\\d'

def test_basename_linux_file():
    linux_file = '/a/b/c/d.txt'
    result = common.basename(linux_file)
    assert result == 'd.txt'

def test_basename_linux_path():
    linux_dir = '/a/b/c/d/'
    result = common.basename(linux_dir)
    assert result == 'd'

def test_basename_win_file():
    win_file = 'A:\\b\\c\\d.txt'
    result = common.basename(win_file)
    assert result == 'd.txt'

def test_basename_win_path():
    win_dir = 'A:\\b\\c\\d\\'
    result = common.basename(win_dir)
    assert result == 'd'

def test_parseDir():
    path = os.path.abspath(os.path.join(MS_WD, 'tests', 'dir_test'))
    result = common.parseDir(path, recursive=False)
    expected = [os.path.join(path, '1.1.txt'), os.path.join(path, '1.2.txt')]
    assert sorted(result) == sorted(expected)
