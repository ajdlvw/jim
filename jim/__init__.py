#/usr/bin/env python2
#
# Copyright (c) 2016, Ilija Hadzic <ilijahadzic@gmail.com>
#
# MIT License, see LICENSE.txt for details

import logging
import web
import ConfigParser
import os
import db
import util
import daemon
import rules
import argparse

_log = None

def read_config(parser):
    cfg = {}
    try:
        cfg['http_port'] = int(parser.get("web", "http_port"))
    except:
        cfg['http_port'] = None
    try:
        cfg['https_port'] = int(parser.get("web", "https_port"))
    except:
        cfg['https_port'] = None
    try:
        cfg['bounce_port'] = int(parser.get("web", "bounce_port"))
    except:
        cfg['bounce_port'] = None
    try:
        cfg['html_root'] = parser.get("web", "html_root")
    except:
        cfg['html_root'] = None
    try:
        cfg['template_root'] = parser.get("web", "template_root")
    except:
        cfg['template_root'] = None
    try:
        cfg['db_file'] = parser.get("db", "db_file")
    except:
        cfg['db_file'] = "./jim.db"
    try:
        cfg['news_file'] = parser.get("db", "news_file")
    except:
        cfg['news_file'] = "./news.txt"
    try:
        cfg['bootstrap_token'] = parser.get("web", "bootstrap_token")
    except:
        cfg['bootstrap_token'] = 'jimimproved'
    try:
        cfg['certs_path'] = parser.get("web", "certs_path")
    except:
        cfg['certs_path'] = None
    try:
        cfg['autoreload'] = parser.get("web", "autoreload")
    except:
        cfg['autoreload'] = False
    try:
        p = parser.get("web", "player_reports_matches")
        if p.lower() == 'true':
            cfg['player_reports_matches'] = True
        else:
            cfg['player_reports_matches'] = False
    except:
        cfg['player_reports_matches'] = False
    _log.info(cfg)
    return cfg

def do_main():
    global _log
    logging.basicConfig(level=logging.DEBUG)
    _log = util.get_syslog_logger("main")
    rules.init()
    config_file_list = [ os.path.dirname(os.path.realpath(__file__)) + '/jim.cfg', '/etc/jim.cfg', './jim.cfg' ]
    config_file_parser = ConfigParser.RawConfigParser()
    config_ok = True
    try:
        config_file_list = config_file_parser.read(config_file_list)
    except:
        _log.error("cannot parse configuration file(s)")
        config_ok = False
    if len(config_file_list) == 0:
        _log.error("no configuration file found")
        config_ok = False
    else:
        _log.info("using configuration files {}".format(config_file_list))
    if config_ok:
        cfg = read_config(config_file_parser)
        _log.info("server configuration: {}".format(cfg))
        _log.info("starting server")
        db_file = cfg.get('db_file')
        if db_file:
            database = db.Database(db_file)
        else:
            database = None
        news = cfg.get('news_file') 
        certs_path = cfg.get('certs_path')
        if certs_path:
            ssl_options = { 'certfile' : certs_path + '/cert.pem',
                            'keyfile': certs_path + '/key.pem' }
        else:
            ssl_options = util.test_ssl_options
        web.run_server(ssl_options = ssl_options, http_port = cfg.get('http_port'), https_port = cfg.get('https_port'), bounce_port = cfg.get('bounce_port'), html_root = cfg.get('html_root'), template_root = cfg.get('template_root'), database = database, news = news, bootstrap_token = cfg.get('bootstrap_token'), player_reports_matches = cfg.get('player_reports_matches'), autoreload = cfg.get('autoreload'))
        _log.info("server exited")
    else:
        _log.error("configuration error")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--nodaemon", help="do not run as a daemon", action="store_true")
    args = parser.parse_args()
    if not args.nodaemon:
        with daemon.DaemonContext():
            do_main()
    else:
        do_main()

if __name__ == "__main__":
    main()
