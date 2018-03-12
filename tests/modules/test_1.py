"""
A test module which requires no config and the result is the filename
"""
TYPE = "Test"
NAME = "test_1"


def check():
    return True


def scan(filelist):
    results = []

    for fname in filelist:
        results.append((fname, fname))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return results, metadata
