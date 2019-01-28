from __future__ import (division, absolute_import, with_statement,
                        print_function, unicode_literals)

import json
import os

from reportlab.lib import colors, units
from reportlab.platypus import TableStyle

from multiscanner.common.pdf_generator import generic_pdf


def create_pdf_document(DIR, report):
    '''
    Method to create a PDF report based of a multiscanner JSON report.

    Args:
        DIR: Represents the a directory containing the 'pdf_config.json' file.
        report: A JSON object.

    '''
    with open(os.path.join(os.path.split(DIR)[0], 'pdf_config.json')) as data_file:
        pdf_components = json.load(data_file)

    gen_pdf = generic_pdf.GenericPDF(pdf_components)

    notice = []

    if pdf_components.get('notification', ''):
        notice = gen_pdf.section('Notification', pdf_components.get('notification'), gen_pdf.style)
    gen_pdf.pdf_list.extend(notice)

    summary = gen_pdf.section('Summary', '', gen_pdf.style)
    gen_pdf.pdf_list.extend(summary)

    summary_data = [
        ['Date Submitted', report.get('Report', {}).get('Scan Time', 'N/A')],
        ['Artifact ID', report.get('Report', {}).get('SHA256', 'N/A')],
        ['Description', pdf_components.get('summary_description', 'N/A')],
        ['Files Processed', '1'],
        ['', report.get('Report', {}).get('filename', 'NO FILENAME AVAILABLE')]
    ]

    gen_pdf.vertical_table(summary_data)

    gen_pdf.line_break()

    file_and_obs = gen_pdf.section('File Indicators and Observables', '', gen_pdf.style)
    gen_pdf.pdf_list.extend(file_and_obs)

    # This list will store data for table under File Indicators and Observables
    file_data = []

    # This list will store data for Yara results. Currently, extracts description of rule. This is a horizontal table.
    yara_data = [['Yara Rule', 'Yara Rule Description']]

    # This list will store AV results. This is a horizontal table.
    av_data = [['Antivirus', 'Scan Result']]

    if 'Report' in report:
        r = report.get('Report', {})
        if 'filename' in r:
            file_data.append(['File Name', r.get('filename', '')])
        if 'Scan Time' in r:
            file_data.append(['Scan Time', r.get('Scan Time', '')])
        if 'libmagic' in r:
            file_data.append(['Type', r.get('libmagic', '')])
        if 'MD5' in r:
            file_data.append(['MD5', r.get('MD5', '')])
        if 'SHA1' in r:
            file_data.append(['SHA1', r.get('SHA1', '')])
        if 'SHA256' in r:
            file_data.append(['SHA256', r.get('SHA256', '')])
        if 'ssdeep' in r:
            file_data.append(['SSDEEP', r.get('ssdeep', {}).get('ssdeep_hash', '')])

        if 'Yara' in r:
            for v in r.get('Yara', {}).values():
                if 'meta' in v:
                    yara_data.append([v.get('rule', 'NO RULE NAME'),
                                      v.get('meta', {}).get('description', 'NO RULE DESCRIPTION')])
        if 'AVG 2014' in r:
            av_data.append(['AVG 2014', r.get('AVG 2014', '')])
        if 'Microsoft Security Essentials' in r:
            av_data.append(['Microsoft Security Essentials', r.get('Microsoft Security Essentials', '')])

        if 'Metadefender' in r:
            engine_results = r.get('Metadefender', {}).get('engine_results', {})
            for av in engine_results:
                threat_found = av.get('threat_found')
                if not threat_found:
                    threat_found = 'No threats found'
                av_data.append([av.get('engine_name'), threat_found])

    if file_data:
        gen_pdf.vertical_table(file_data)

    gen_pdf.line_break()

    av_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.skyblue),
    ])

    gen_pdf.horizontal_table(av_data, av_table_style, (50 * units.mm, 140 * units.mm))

    gen_pdf.line_break()

    yara_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.skyblue),
    ])

    gen_pdf.horizontal_table(yara_data, yara_table_style, (50 * units.mm, 140 * units.mm))

    gen_pdf.line_break()

    mitigation_recommendation = gen_pdf.section(
        'Mitigation Recommendations', pdf_components.get('mitigation_recommendations', ''), gen_pdf.style)

    for mr in mitigation_recommendation:
        gen_pdf.pdf_list.append(mr)

    mitigation_bullets = gen_pdf.bullet_list(pdf_components.get('mitigation_bullet_list', ''), 1)
    gen_pdf.pdf_list.append(mitigation_bullets)

    gen_pdf.line_break()

    contact = gen_pdf.section('Contact Information', pdf_components.get('contact_information', ''), gen_pdf.style)

    for c in contact:
        gen_pdf.pdf_list.append(c)

    faq = gen_pdf.section('Document FAQ', pdf_components.get('document_faq', ''), gen_pdf.style)

    for f in faq:
        gen_pdf.pdf_list.append(f)

    return gen_pdf.build()
