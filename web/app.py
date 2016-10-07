import argparse
from flask import (Flask, render_template, request, redirect, url_for, make_response, flash)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', methods=['GET'])


@app.route('/tasks')
def tasks():
    return render_template('tasks.html', methods=['GET'])


@app.route('/report/<int:task_id>', methods=['GET'])
def reports(task_id=1):
    return render_template('report.html', task_id=task_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help="Host to bind the API server on",
                        default="localhost", action="store", required=False)
    parser.add_argument("-p", "--port", help="Port to bind the API server on",
                        default=8000, action="store", required=False)
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debug mode (NOT for production!)")
    args = parser.parse_args()

    app.run(debug=args.debug, port=args.port, host=args.host)
