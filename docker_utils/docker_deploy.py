import argparse
import logging
import multiprocessing
import os
import sys

from gevent.pywsgi import WSGIServer


def _parse_args():
    """
    Parses arguments
    """
    parser = argparse.ArgumentParser(description="Small script to deploy WSGI Server in Docker")
    parser.add_argument("-l", "--logging-level", help="Logging level to use", action="store", default="DEBUG",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("run", help="Which type of application to run")
    return parser.parse_args()


if __name__ == '__main__':
    args = _parse_args()

    if args.run == 'api':
        from multiscanner.distributed.api import app as api_app
        from multiscanner.distributed.api import api_config, multiscanner_process, work_queue

        logging.basicConfig(level=logging.getLevelName(args.logging_level))

        if not os.path.isdir(api_config['api']['upload_folder']):
            logging.info('Creating upload dir')
            os.makedirs(api_config['api']['upload_folder'])

        exit_signal = multiprocessing.Value('b')
        exit_signal.value = False
        ms_process = multiprocessing.Process(
            target=multiscanner_process,
            args=(work_queue, exit_signal)
        )
        ms_process.start()

        http_server = WSGIServer((api_config['api']['host'],
                                  api_config['api']['port']), api_app)
        http_server.serve_forever()

        ms_process.join()

    elif args.run == 'web':
        from multiscanner.web.app import app as web_app
        from multiscanner.web.app import DEFAULTCONF

        logging.basicConfig(level=logging.getLevelName(args.logging_level))
        http_server = WSGIServer((web_app.config.get('HOST', DEFAULTCONF['HOST']),
                                  web_app.config.get('PORT', DEFAULTCONF['PORT'])), web_app)
        http_server.serve_forever()
    else:
        msg = "Error occurred while trying to instantiate Docker Instance. Arguments {}"
        raise RuntimeError(msg.format(sys.argv))
