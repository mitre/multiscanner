"""
A test module which tests that config handling works
"""
TYPE = "Test"
NAME = "test_subscan"

# Overwritten in multiscanner
multiscanner = None


def check():
    return True


def scan(filelist):
    results = []

    for f in filelist:
        results.append((f, multiscanner.run_count))
        if multiscanner.run_count < 2:
            multiscanner.scan_file(str(multiscanner.run_count), f)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return results, metadata
