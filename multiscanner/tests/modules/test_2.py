"""
A test module which has a required module and a config
"""
TYPE = "Test"
NAME = "test_2"
REQUIRES = ["test_1"]
DEFAULTCONF = {'a': 1, 'b': 2}


def check(conf=DEFAULTCONF):
    if None in REQUIRES:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    result1, meta1 = REQUIRES[0]
    result1 = dict(result1)

    for fname in filelist:
        if fname in result1:
            results.append((fname, True))
        else:
            results.append((fname, fname))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = True
    return results, metadata
