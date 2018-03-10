import json
import os
import sys

import stix2

'''Test module for STIX2 content generation methods'''

CWD = os.path.dirname(os.path.abspath(__file__))
MODULE_TEST_DIR = os.path.dirname(CWD)
TEST_DIR = os.path.dirname(MODULE_TEST_DIR)
MS_WD = os.path.dirname(TEST_DIR)


# Allow import of stix2_generator
if os.path.join(MS_WD, 'utils') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'utils'))
# Use multiscanner in ../
sys.path.insert(0, os.path.dirname(CWD))

import stix2_generator


def test_create_empty_bundle():
    bundle = stix2_generator.create_stix2_bundle([])
    assert isinstance(bundle, stix2.Bundle)


def test_create_non_empty_bundle():
    indicator1 = stix2.Indicator(**{
        'labels': ['benign'],
        'pattern': '[ ipv4-addr:value = \'198.51.100.1/32\' ]'
    })
    indicator2 = stix2.Indicator(**{
        'labels': ['benign'],
        'pattern': '[ ipv4-addr:value = \'203.0.113.33/32\' ]'
    })
    bundle = stix2_generator.create_stix2_bundle([indicator1, indicator2])

    assert isinstance(bundle, stix2.Bundle)
    assert bundle.type == 'bundle'
    assert bundle.id.startswith('bundle--')
    assert bundle.spec_version == '2.0'
    assert all(x in bundle.objects for x in (indicator1, indicator2))


def test_join_comparison_expression():
    exp = stix2_generator.join_stix2_comparison_expression(
        ['ipv4-addr:value = \'198.51.100.1/32\'',
         'ipv4-addr:value = \'203.0.113.33/32\''], 'OR')

    assert exp == ('ipv4-addr:value = \'198.51.100.1/32\' OR '
                   'ipv4-addr:value = \'203.0.113.33/32\'')


def test_create_comparison_expression():
    exp = stix2_generator.create_stix2_comparison_expression(
        'ipv4-addr:value',
        '=',
        '198.51.100.1/32'
    )

    assert exp == 'ipv4-addr:value = \'198.51.100.1/32\''


def test_create_observation_expression():
    comparison_exp = stix2_generator.create_stix2_comparison_expression(
        'ipv4-addr:value',
        '=',
        '198.51.100.1/32'
    )

    observation_exp = stix2_generator.create_sti2_observation_expression(
        comparison_exp
    )

    assert observation_exp == '[ ipv4-addr:value = \'198.51.100.1/32\' ]'


def test_create_observation_expression_list():
    comparison_exp_1 = stix2_generator.create_stix2_comparison_expression(
        'ipv4-addr:value',
        '=',
        '198.51.100.1/32'
    )

    comparison_exp_2 = stix2_generator.create_stix2_comparison_expression(
        'ipv4-addr:value',
        '=',
        '203.0.113.33/32'
    )

    all_comparison_exp = [comparison_exp_1, comparison_exp_2]

    observation_exp = stix2_generator.create_sti2_observation_expression(
        all_comparison_exp, 'OR'
    )

    assert observation_exp == ('[ ipv4-addr:value = \'198.51.100.1/32\' OR '
                               'ipv4-addr:value = \'203.0.113.33/32\' ]')


def test_extract_file_cuckoo():
    all_indicators_expressions = [
        '[ file:name = \'s2429.exe.zip\' OR file:hashes.\'SHA-1\' = \'388e6816aff442e13cb546cfacd0c1d75b59b5b1\' OR file:hashes.\'SHA-256\' = \'1acf42374fb021fd1172df27a06f72e0e59f69a0bfaaaaea56f28dff6af01110\' OR file:hashes.\'MD5\' = \'d659e8900ea3fabe425882debed0c494\' ]',
        '[ file:name = \'s2429.exe\' OR file:hashes.\'SHA-1\' = \'ddf811f21e6c066b644d03e6751e16efb0fbecce\' OR file:hashes.\'SHA-256\' = \'f9449897f9ca99b99837ad322c8b6737e7a47e3827b6a4c073c6ca8911d8c340\' OR file:hashes.\'MD5\' = \'13b0085a03720e67fb8c73db3f14609e\' ]'
    ]
    extracted_indicator_expressions = []

    with open(os.path.join(CWD, 'sample_report.json')) as sample_report:
        sample_json = json.load(sample_report)
        r = sample_json.get('Report', {})
        cuckoo = r.get('Cuckoo Sandbox', {})

        for d in cuckoo.get('dropped', []):
            extracted_indicator_expressions.append(
                stix2_generator.extract_file_cuckoo(d).pattern
            )

    assert all(x in all_indicators_expressions for x in extracted_indicator_expressions)


def test_extract_http_requests_cuckoo():
    all_indicators_expressions = [
        '[ url:value = \'http://www.msftncsi.com/ncsi.txt\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?ec38990cc55170ab\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:2144477707&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:3255292227&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:1128284371&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:1439439368&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/disallowedcertstl.cab?075dc50dacf9f2bb\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?31308c2120fea4bc\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?6ecb1b8de9d8006f\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?91c8a9092e8cb67a\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?1390637153eb96bd\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?b16bed41061b4861\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?9a8ede518893069d\' ]',
        '[ url:value = \'http://go.microsoft.com/fwlink/?LinkId=544713\' ]'
    ]
    extracted_indicator_expressions = []

    with open(os.path.join(CWD, 'sample_report.json')) as sample_report:
        sample_json = json.load(sample_report)
        r = sample_json.get('Report', {})
        cuckoo = r.get('Cuckoo Sandbox', {})

        for s in cuckoo.get('signatures', []):
            if 'description' in s and 'HTTP request' in s.get('description', ''):
                extracted_indicator_expressions.extend([
                    x.pattern
                    for x in stix2_generator.extract_http_requests_cuckoo(s)
                ])

    assert all(x in all_indicators_expressions for x in extracted_indicator_expressions)


def test_parse_json_report_to_stix2_bundle():
    all_indicators_expressions = [
        '[ file:name = \'s2429.exe.zip\' OR file:hashes.\'SHA-1\' = \'388e6816aff442e13cb546cfacd0c1d75b59b5b1\' OR file:hashes.\'SHA-256\' = \'1acf42374fb021fd1172df27a06f72e0e59f69a0bfaaaaea56f28dff6af01110\' OR file:hashes.\'MD5\' = \'d659e8900ea3fabe425882debed0c494\' ]',
        '[ file:name = \'s2429.exe\' OR file:hashes.\'SHA-1\' = \'ddf811f21e6c066b644d03e6751e16efb0fbecce\' OR file:hashes.\'SHA-256\' = \'f9449897f9ca99b99837ad322c8b6737e7a47e3827b6a4c073c6ca8911d8c340\' OR file:hashes.\'MD5\' = \'13b0085a03720e67fb8c73db3f14609e\' ]',
        '[ url:value = \'http://www.msftncsi.com/ncsi.txt\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?ec38990cc55170ab\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:2144477707&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:3255292227&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:1128284371&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://tools.google.com/service/update2?cup2key=6:1439439368&cup2hreq=a6c83ff1daef97153eb6f265f9181edc5cea9a80f527aea825c28f6307c1fdfc\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/disallowedcertstl.cab?075dc50dacf9f2bb\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?31308c2120fea4bc\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?6ecb1b8de9d8006f\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?91c8a9092e8cb67a\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?1390637153eb96bd\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?b16bed41061b4861\' ]',
        '[ url:value = \'http://ctldl.windowsupdate.com/msdownload/update/v3/static/trustedr/en/authrootstl.cab?9a8ede518893069d\' ]',
        '[ url:value = \'http://go.microsoft.com/fwlink/?LinkId=544713\' ]',
        '[ url:value = \'http://ns.adobe.com/xap/1.0/mm/\' ]',
        '[ url:value = \'http://ns.adobe.com/xap/1.0/sType/ResourceRef\' ]',
        '[ url:value = \'http://ns.adobe.com/xap/1.0/\' ]',
        '[ file:hashes.\'SHA-1\' = \'91fd2d2935aedcb47271b54cd22f8fe3b30c17fd\' OR file:hashes.\'SHA-256\' = \'90b1e39282dbda2341d91b87ca161afe564b7d3b4f82f25b3f1dce3fa857226c\' OR file:hashes.\'MD5\' = \'34303fdb55e5d0f1142bb07eed2064cb\' ]'
    ]
    extracted_indicator_expressions = []

    with open(os.path.join(CWD, 'sample_report.json')) as sample_report:
        sample_json = json.load(sample_report)
        bundle = stix2_generator.parse_json_report_to_stix2_bundle(sample_json)

        for x in bundle.objects:
            if isinstance(x, stix2.Indicator):
                extracted_indicator_expressions.append(x.pattern)

    assert all(x in all_indicators_expressions for x in extracted_indicator_expressions)
