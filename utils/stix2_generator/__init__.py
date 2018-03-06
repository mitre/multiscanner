from __future__ import (division, absolute_import, with_statement,
                        print_function, unicode_literals)

import stix2


def create_stix2_bundle(objects):
    '''
    Creates a STIX2 Bundle object from a list of objects.

    Args:
        objects: list of ``stix2`` SDO objects.

    Returns:
        A ``stix2.Bundle`` instance.

    '''
    return stix2.Bundle(objects=objects)


def join_stix2_comparison_expression(comp_exps, obs_operator):
    '''
    Joins multiple comparison expressions using the same observable operator.

    Args:
        comp_exps: A list of comparison expressions
        obs_operator: A observation operator (e.g., 'OR' or 'AND')

    Returns:
        str: Containing the full observation expression joined by the specified
            operator.

    Example:
        >>> join_stix2_comparison_expression(
        ...     ['ipv4-addr:value = \\'198.51.100.1/32\\'',
        ...     'ipv4-addr:value = \\'203.0.113.33/32\\''], 'OR')
        'ipv4-addr:value = \'198.51.100.1/32\' OR ipv4-addr:value = \'203.0.113.33/32\''

    '''
    return " {observation_operator} ".format(observation_operator=
                                             obs_operator).join(comp_exps)


def create_stix2_comparison_expression(lhs, op, rhs):
    '''
    Creates a comparison expression.

    Args:
        lhs: A string containing the left-hand side of the expression
        op: A string containing the operator to use.
        rhs: A string containing the right-hand side of the expression.

    Returns:
        str: Containing the comparison expression.

    References:
        For more information on STIX2 patterning visit
        http://docs.oasis-open.org/cti/stix/v2.0/cs01/part5-stix-patterning/stix-v2.0-cs01-part5-stix-patterning.html

    '''
    return '{lhs} {op} \'{rhs}\''.format(lhs=lhs, op=op, rhs=rhs)


def create_sti2_observation_expression(comp_exps, obs_operator=None):
    '''
    Given comparison expression(s) create an observation expression.

    Args:
        comp_exps: a list of comparison expressions or single comparison
            expression to generate an observation expression.
        obs_operator: A observation operator (e.g., 'OR' or 'AND'). Required
            when a list of comparison expressions is provided.

    Returns:
        A STIX2 comparison expression pattern.

    References:
        For more information on STIX2 patterning visit
        http://docs.oasis-open.org/cti/stix/v2.0/cs01/part5-stix-patterning/stix-v2.0-cs01-part5-stix-patterning.html

    '''
    if isinstance(comp_exps, list) and len(comp_exps) > 1:
        # The obs_operator is required for this operation.
        return '[ {pattern} ]'.format(pattern=
                                      join_stix2_comparison_expression(
                                          comp_exps, obs_operator
                                      ))
    elif len(comp_exps) == 1:
        return '[ {pattern} ]'.format(pattern=comp_exps[0])
    return '[ {pattern} ]'.format(pattern=comp_exps)


def extract_file_cuckoo(dropped_file):
    '''
    Process a Cuckoo dropped file obtained from analysis.

    Args:
        dropped_file: A dict from the "dropped" list from the "Cuckoo Sandbox"
            report.

    Returns:
        ``stix2.Indicator`` with a pattern that matches the file by name or
            a variety of hashes.

    '''
    labels = ['benign']
    dropped_pattern = []

    file_name = dropped_file.get('filepath', '')
    sha1_value = dropped_file.get('sha1', '')
    sha256_value = dropped_file.get('sha256', '')
    md5_value = dropped_file.get('md5', '')

    if file_name:
        file_name = file_name.split("\\")[-1]
        dropped_pattern.append(
            create_stix2_comparison_expression('file:name', '=', file_name)
        )

    if sha1_value:
        dropped_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'SHA-1\'', '=',
                                               sha1_value)
        )

    if sha256_value:
        dropped_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'SHA-256\'', '=',
                                               sha256_value)
        )

    if md5_value:
        dropped_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'MD5\'', '=',
                                               md5_value)
        )

    return stix2.Indicator(**{
        'labels': labels,
        'pattern': create_sti2_observation_expression(dropped_pattern, 'OR')
    })


def extract_http_requests_cuckoo(marks_list, severity):
    '''
    Process Cuckoo http signatures obtained from analysis.

    Args:
        marks_list: A list of http marks from the "signatures" list in the
            "Cuckoo Sandbox" report.
        severity: The severity score from the "signatures". (range 1 to 3)

    Returns:
        list: Containing ``stix2.Indicator`` with a pattern that matches the
            file by name or a variety of hashes.

    '''
    indicators = []
    labels = []

    if severity <= 2:
        labels.extend(['benign', 'anomalous-activity'])
    else:
        labels.append('anomalous-activity')

    for ioc_mark in marks_list:
        ioc = ioc_mark.get('ioc', '')
        if ioc:
            url_value = ioc.split()[1]
            ioc_pattern = create_sti2_observation_expression(
                create_stix2_comparison_expression('url:value', '=', url_value)
            )
            indicators.append(stix2.Indicator(**{
                'labels': labels,
                'pattern': ioc_pattern
            }))

    return indicators


def parse_json_report_to_stix2_bundle(report):
    '''
    Creates a STIX2 bundle from a multiscanner JSON report. This is achieved
    on a best effort approach and does not intend to capture all possible
    cases.

    Args:
        report: The dict representation of a multiscanner report.

    Returns:
        ``stix2.Bundle`` with Indicators generated from the report.

    Notes:
        There might be more content present in the report that may not
        be represented as STIX simply because neccessary logic to process
        that content is missing.

    '''
    all_objects = []
    r = report.get('Report', {})

    cuckoo = r.get('Cuckoo Sandbox', {})

    for c in cuckoo:  # Use this block to extract further content from cuckoo
        for signature in c.get('signatures', []):
            if ('description' in signature
                    and 'HTTP request' in signature.get('description', '')):
                all_objects.extend(extract_http_requests_cuckoo(
                    signature.get('marks', []),
                    signature.get('severity', 1)
                ))
        for dropped in c.get('dropped', []):
            if dropped and ('sha256', 'md5', 'sha1') in dropped:
                all_objects.append(extract_file_cuckoo(dropped))

    # Extract information from file submission and create Indicator
    submission_pattern = []
    file_name = r.get('filename', '')
    sha1_value = r.get('SHA1', '')
    sha256_value = r.get('SHA256', '')
    md5_value = r.get('MD5', '')

    if file_name:
        submission_pattern.append(
            create_stix2_comparison_expression('file:name', '=', file_name)
        )

    if sha1_value:
        submission_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'SHA-1\'', '=',
                                               sha1_value)
        )

    if sha256_value:
        submission_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'SHA-256\'', '=',
                                               sha256_value)
        )

    if md5_value:
        submission_pattern.append(
            create_stix2_comparison_expression('file:hashes.\'MD5\'', '=',
                                               md5_value)
        )

    if submission_pattern:
        all_objects.append(stix2.Indicator(**{
            'labels': ['benign'],
            'pattern': create_sti2_observation_expression(submission_pattern,
                                                          'OR')
        }))

    return create_stix2_bundle(all_objects)
