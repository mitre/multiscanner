"""
A test module which tests that config handling works
"""
TYPE = "Test"
NAME = "test_subscan"
DEFAULTCONF = {
    'ENABLED': True
}

# Overwritten in multiscanner
multiscanner = None


def check(conf=DEFAULTCONF):
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for f in filelist:
        results.append((f, multiscanner.run_count))
        if multiscanner.run_count < 2:
            multiscanner.scan_file(str(multiscanner.run_count), f)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return results, metadata
