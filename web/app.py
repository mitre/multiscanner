import codecs
from collections import namedtuple
import configparser
from flask import Flask, render_template, request
import os
import re
import sys

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MS_WD not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD))
import multiscanner

DEFAULTCONF = {
    'HOST': "localhost",
    'PORT': 8000,
    'API_LOC': "http://localhost:8080",
    'DEBUG': False,
    'METADATA_FIELDS': [
        "Submitter Name",
        "Submission Description",
        "Submitter Email",
        "Submitter Organization",
        "Submitter Phone",
    ]
}

app = Flask(__name__)

# Finagle Flask to read config from .ini file instead of .py file
web_config_object = configparser.SafeConfigParser()
web_config_object.optionxform = str
web_config_file = multiscanner.common.get_config_path(multiscanner.CONFIG, 'web')
web_config_object.read(web_config_file)
if not web_config_object.has_section('web') or not os.path.isfile(web_config_file):
    # Write default config
    web_config_object.add_section('web')
    for key in DEFAULTCONF:
        web_config_object.set('web', key, str(DEFAULTCONF[key]))
    conffile = codecs.open(web_config_file, 'w', 'utf-8')
    web_config_object.write(conffile)
    conffile.close()
web_config = multiscanner.common.parse_config(web_config_object)['web']
conf_tuple = namedtuple('WebConfig', web_config.keys())(*web_config.values())
app.config.from_object(conf_tuple)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', api_loc=app.config['API_LOC'],
                           metadata_fields=app.config['METADATA_FIELDS'])


@app.route('/analyses', methods=['GET', 'POST'])
def tasks():
    if request.method == 'POST':
        return render_template('analyses.html', api_loc=app.config['API_LOC'],
                               search_term=request.form['search_term'],
                               search_type=request.form['search_type_buttons'])
    else:
        return render_template('analyses.html', api_loc=app.config['API_LOC'])


@app.route('/report/<int:task_id>', methods=['GET'])
def reports(task_id=1):
    term = re.escape(request.args.get('st', None))

    return render_template('report.html', task_id=task_id,
                           api_loc=app.config['API_LOC'], search_term=term)


@app.route('/history', methods=['GET', 'POST'])
def history():
    if request.method == 'POST':
        return render_template('history.html', api_loc=app.config['API_LOC'],
                               search_term=request.form['search_term'],
                               search_type=request.form['search_type_buttons'])
    else:
        return render_template('history.html', api_loc=app.config['API_LOC'])


if __name__ == "__main__":
    app.run(debug=app.config['DEBUG'],
            port=app.config['PORT'],
            host=app.config['HOST'])
