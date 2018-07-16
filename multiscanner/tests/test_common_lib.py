import os
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from multiscanner.common import utils


def test_list2cmdline():
    ls = ['1', 'a', '"dsafsad"']
    result = '1 a "dsafsad"'
    assert utils.list2cmdline(ls) == result


def test_dirname_linux_file():
    linux_file = '/a/b/c/d.txt'
    result = utils.dirname(linux_file)
    assert result == '/a/b/c'


def test_dirname_linux_path():
    linux_dir = '/a/b/c/d/'
    result = utils.dirname(linux_dir)
    assert result == '/a/b/c/d'


def test_dirname_win_file():
    win_file = 'A:\\b\\c\\d.txt'
    result = utils.dirname(win_file)
    assert result == 'A:\\b\\c'


def test_dirname_win_path():
    win_dir = 'A:\\b\\c\\d\\'
    result = utils.dirname(win_dir)
    assert result == 'A:\\b\\c\\d'


def test_basename_linux_file():
    linux_file = '/a/b/c/d.txt'
    result = utils.basename(linux_file)
    assert result == 'd.txt'


def test_basename_linux_path():
    linux_dir = '/a/b/c/d/'
    result = utils.basename(linux_dir)
    assert result == 'd'


def test_basename_win_file():
    win_file = 'A:\\b\\c\\d.txt'
    result = utils.basename(win_file)
    assert result == 'd.txt'


def test_basename_win_path():
    win_dir = 'A:\\b\\c\\d\\'
    result = utils.basename(win_dir)
    assert result == 'd'


def test_parseDir():
    path = os.path.abspath(os.path.join(MS_WD, 'tests', 'dir_test'))
    result = utils.parseDir(path, recursive=False)
    expected = [os.path.join(path, '1.1.txt'), os.path.join(path, '1.2.txt')]
    assert sorted(result) == sorted(expected)
