from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import cgi

import six

from reportlab.lib.colors import red, orange, lawngreen, white, black, blue
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Spacer, Image, Paragraph,
                                ListFlowable, ListItem, TableStyle, Table)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont('Helvetica-Bold', 7)
        self.drawRightString(203 * mm, 12.7 * mm,
                             'Page %d of %d' % (self._pageNumber, page_count))


class GenericPDF(object):

    def __init__(self, pdf_components):
        self.style = getSampleStyleSheet()
        self.style['Normal'].leading = 16
        self.style.add(ParagraphStyle(name='centered', alignment=TA_CENTER))
        self.style.add(ParagraphStyle(name='centered_wide', alignment=TA_CENTER,
                                      leading=18))
        self.style.add(ParagraphStyle(name='section_body',
                                      parent=self.style['Normal'],
                                      spaceAfter=inch * .05,
                                      fontSize=11))
        self.style.add(ParagraphStyle(name='bullet_list',
                                      parent=self.style['Normal'],
                                      fontSize=11))
        if six.PY3:
            self.buffer = six.BytesIO()
        else:
            self.buffer = six.StringIO()
        self.firstPage = True
        self.document = SimpleDocTemplate(self.buffer, pagesize=letter,
                                          rightMargin=12.7 * mm, leftMargin=12.7 * mm,
                                          topMargin=120, bottomMargin=80)

        self.tlp_color = pdf_components.get('tlp_color', '')
        self.pdf_components = pdf_components
        self.pdf_list = []

    def line_break(self, spaces=25):
        self.pdf_list.append(Spacer(1, spaces))

    def header_footer(self, canvas, doc):
        canvas.saveState()
        height_adjust = self.add_banner(canvas, doc)

        # Document Header
        if self.pdf_components.get('hdr_image', None) and self.firstPage:
            header = Image(self.pdf_components.get('hdr_image'), height=25 * mm, width=191 * mm)
            header.drawOn(canvas, doc.rightMargin, doc.height + doc.topMargin - 15 * mm)
            self.firstPage = False
        elif self.firstPage:
            header = Paragraph(self.pdf_components.get('hdr_html', ''), self.style['centered'])
            w, h = header.wrap(doc.width, doc.topMargin)
            header.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - height_adjust * h)

        # Document Footer
        if self.pdf_components.get('ftr_image', None):
            footer = Image(self.pdf_components.get('ftr_image'), 8.5 * inch, 1.8 * inch)
            footer.drawOn(canvas, 0, 0)
        else:
            footer = Paragraph(self.pdf_components.get('ftr_html', ''), self.style['centered'])
            w, h = footer.wrap(doc.width, doc.bottomMargin)
            footer.drawOn(canvas, doc.leftMargin, height_adjust * h)

        # Release the Canvas
        canvas.restoreState()

    def add_banner(self, canvas, doc):
        height_adjust = 1
        if self.tlp_color:
            if self.tlp_color == 'WHITE':
                text_color = white
            elif self.tlp_color == 'RED':
                text_color = red
            elif self.tlp_color == 'AMBER':
                text_color = orange
            else:
                text_color = lawngreen
                self.tlp_color = 'GREEN'

            if 'banner_style' not in self.style:
                self.style.add(ParagraphStyle(name='banner_style',
                                              textColor=text_color,
                                              textTransform='uppercase',
                                              alignment=TA_RIGHT))

            banner = Paragraph(
                self.span_text(self.bold_text('TLP:' + self.tlp_color), bgcolor='black'),
                self.style['banner_style'])
            w, h = banner.wrap(doc.width, doc.topMargin)
            banner.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin + (h + 12 * mm))
            w, h = banner.wrap(doc.width, doc.bottomMargin)
            banner.drawOn(canvas, doc.leftMargin, h + 12 * mm)

            height_adjust = 3

        return height_adjust

    def same_line(self, label, body):
        return Paragraph(self.bold_text(label) + ':  ' + body, self.style['section_body'])

    def section(self, title, body, is_header=False):
        if is_header:
            section_header = self.style['Heading1']
        else:
            section_header = self.style['Heading2']
            title = self.underline_text(title)
            body = cgi.html.escape(body)

        items = []
        headline = Paragraph(title, section_header)
        items.append(headline)

        for paragraph in body.split('<br/><br/>'):
            try:
                para = Paragraph(paragraph + '<br/><br/>', self.style['section_body'])
                items.append(para)
            except Exception as e:
                print('Error Creating PDF: ' + str(e))

        return items

    def bullet_list(self, body, level):
        items = []

        for text_line in body.split('<br/>'):
            try:
                bullet_text = ListItem(Paragraph(text_line, self.style['bullet_list']),
                                       leftIndent=level * 35,
                                       value='bulletchar')
                items.append(bullet_text)
            except Exception as e:
                print('Error Creating PDF: ' + str(e))

        return ListFlowable(items, bulletType='bullet', start='bulletchar')

    def vertical_table(self, data, table_style=None, col_widths=None):
        '''A table where the first column is bold. A label followed by values.'''
        self.style['BodyText'].wordWrap = 'LTR'
        self.style['BodyText'].spaceBefore = 2

        if table_style:
            style = table_style
        else:
            style = TableStyle([
                ('LINEABOVE', (0, 0), (-1, 0), 0.75, blue),
                ('BOX', (1, 0), (0, -1), 0.25, black),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT')
            ])

        if col_widths:
            cols = col_widths
        else:
            cols = (35 * mm, 140 * mm)

        data2 = [[Paragraph(self.bold_text(cell), self.style['BodyText']) if idx == 0
                  else Paragraph(cell, self.style['BodyText'])
                  for idx, cell in enumerate(row)] for row in data]

        table = Table(data2, style=style, colWidths=cols)
        self.pdf_list.append(table)

    def horizontal_table(self, data, table_style=None, col_widths=None):
        '''A table where the first row is bold. The first row are labels, the rest values.'''
        self.style['BodyText'].wordWrap = 'LTR'
        self.style['BodyText'].spaceBefore = 2

        if table_style:
            style = table_style
        else:
            style = TableStyle([
                ('LINEABOVE', (0, 0), (-1, 0), 0.75, blue),
                ('BOX', (1, 0), (0, -1), 0.25, black),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT')
            ])

        if col_widths:
            cols = col_widths
        else:
            cols = (35 * mm, 140 * mm)

        data2 = [[Paragraph(self.bold_text(cell), self.style['BodyText']) if idx == 0
                  else Paragraph(cell, self.style['BodyText'])
                  for cell in row] for idx, row in enumerate(data)]

        table = Table(data2, style=style, colWidths=cols)
        self.pdf_list.append(table)

    def build(self):
        self.pdf_list.append(Paragraph(' ', self.style['centered']))
        self.document.build(self.pdf_list,
                            onFirstPage=self.header_footer,
                            onLaterPages=self.header_footer,
                            canvasmaker=NumberedCanvas)

        pdf = self.buffer.getvalue()
        self.buffer.close()

        return pdf

    @staticmethod
    def bold_text(text):
        return '<b>' + text + '</b>'

    @staticmethod
    def underline_text(text):
        return '<u>' + text + '</u>'

    @staticmethod
    def span_text(text, **kwargs):
        return '<span {props}>{text}</span>'.format(text=text,
                                                    props=' '.join('{0}="{1}"'.format(k, v)
                                                                   for k, v in kwargs.items()))
