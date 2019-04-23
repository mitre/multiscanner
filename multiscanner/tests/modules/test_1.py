"""
A test module which requires no config and the result is the filename
"""
TYPE = "Test"
NAME = "test_1"
DEFAULTCONF = {
    'ENABLED': True
}


def check(conf=DEFAULTCONF):
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for fname in filelist:
        results.append((fname, fname))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return results, metadata
