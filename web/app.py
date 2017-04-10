from flask import (Flask, render_template, request, redirect, url_for, make_response, flash)

app = Flask(__name__)
app.config.from_object('config')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', api_loc=app.config['API_LOC'],
                           metadata_fields=app.config['METADATA_FIELDS'])


@app.route('/tasks', methods=['GET'])
def tasks():
    return render_template('tasks.html', api_loc=app.config['API_LOC'])


@app.route('/report/<int:task_id>', methods=['GET'])
def reports(task_id=1):
    return render_template('report.html', task_id=task_id,
                           api_loc=app.config['API_LOC'])


if __name__ == "__main__":
    app.run(debug=app.config['DEBUG'],
            port=app.config['PORT'],
            host=app.config['HOST'])
