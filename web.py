#!/usr/bin/env python2

import tornado
import log
import datetime
from tornado import web, httpserver

_http_server = None
_https_server = None
_template_root = './templates'
_log = None
# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
_test_ssl_options = { 'certfile' : './certs/cert.pem', 'keyfile': './certs/key.pem' }

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/index.html', permanent = True)

class DateHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('date.html', date_string = str(datetime.datetime.now()))

def run_server(ssl_options = _test_ssl_options, http_port = 80, https_port = 443, log_facility = None, html_root = './html', template_root = './templates'):
    global _http_server
    global _https_server
    global _log

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/date', DateHandler)
        ]

    if log_facility:
        _log = log_facility
    else:
        _log = log.TrivialLogger()

    handlers.append(('/(.*)', web.StaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers = handlers, template_path = template_root)
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
