#!/usr/bin/env python2

import tornado
import logging
import datetime
import os
import sys
import binascii
import rules
import util
from tornado import web, httpserver
from datetime import datetime
from datetime import timedelta

_http_server = None
_https_server = None
_template_root = sys.prefix + '/var/jim/templates'
_log = None
# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
_test_ssl_options = { 'certfile' : sys.prefix + '/var/jim/certs/cert.pem', 'keyfile': sys.prefix + '/var/jim/certs/key.pem' }

class DynamicBaseHandler(tornado.web.RequestHandler):
    def finish_failure(self, err = None):
        retval = { 'result': 'failure', 'reason': err }
        self.finish(retval)

    def finish_success(self, args = {}):
        retval = { 'result': 'success' }
        retval.update(args)
        self.finish(retval)

    def get_args(self):
        try:
            args = self.request.query_arguments
            return args
        except:
            self.finish_failure("query parse error")
            return None

    def get_player_args(self, args, mandatory):
        try:
            first_name = args['first_name'][0]
        except:
            if mandatory:
                self.finish_failure("player fist name missing")
                return None
            else:
                first_name = None
        try:
            last_name = args['last_name'][0]
        except:
            if mandatory:
                self.finish_failure("player last name missing")
                return None
            else:
                last_name = None
        try:
            home_phone = args['home_phone'][0]
        except:
            home_phone = None
        try:
            cell_phone = args['cell_phone'][0]
        except:
            cell_phone = None
        try:
            work_phone = args['work_phone'][0]
        except:
            work_phone = None
        if mandatory and not (home_phone or cell_phone or work_phone):
            self.finish_failure("at least one phone number is required")
            return None
        try:
            email = args['email'][0]
        except:
            if mandatory:
                self.finish_failure("e-mail is required")
                return None
            else:
                email = None
        try:
            ladder = args['ladder'][0].lower()
        except:
            if mandatory:
                ladder = 'unranked'
            else:
                ladder = None
        try:
            company = args['company'][0]
        except:
            if mandatory:
                self.finish_failure("company name is required")
                return None
            else:
                company = None
        if mandatory and not ladder in [ 'a', 'b', 'c', 'unranked', 'beginner' ]:
            self.finish_failure("invalid ladder category")
            return None
        try:
            initial_points_str = args['initial_points'][0]
        except:
            if mandatory:
                initial_points_str = '0'
            else:
                initial_points_str = None
        if initial_points_str:
            try:
                initial_points = int(initial_points_str)
            except:
                self.finish_failure("initial ladder points must be an integer")
                return None
            if initial_points < 0:
                self.finish_failure("initial ladder points cannot be negative")
                return None
        else:
            initial_points = None
        try:
            active = util.str_to_bool(args['active'][0])
            if active == None:
                self.finish_failure("active-flag must be boolean")
                return
        except:
            if mandatory:
                active = True
            else:
                active = None
        player = {'first_name': first_name,
                  'last_name' : last_name,
                  'email' : email,
                  'home_phone' : home_phone,
                  'work_phone' : work_phone,
                  'cell_phone' : cell_phone,
                  'company': company,
                  'ladder': ladder,
                  'initial_points': initial_points,
                  'active': active}
        if mandatory:
            return player
        else:
            return util.purge_null_fields(player)

    def get_account_args(self, args, mandatory):
        try:
            account_type = args['type'][0]
        except:
            if mandatory:
                self.finish_failure('account type missing')
                return None
            else:
                account_type = None
        try:
            username = args['username'][0]
        except:
            if mandatory:
                self.finish_failure('username missing')
                return None
            else:
                username = None
        if not account_type:
            # can happen only for account updates
            player_ids = args.get('player_id')
            if player_ids:
                player_id = player_ids[0]
            else:
                player_id = None
        elif account_type == 'admin':
            if args.get('player_id'):
                self.finish_failure('admin account cannot be associated with a player')
                return None
        else:
            try:
                player_id = args['player_id'][0]
            except:
                self.finish_failure('regular account must be associated with a player')
                return None
        if mandatory:
            try:
                password = args['password'][0]
            except:
                self.finish_failure('password missing')
                return None
        else:
            password = None
        if account_type == 'admin':
            account = {'type' : account_type,
                       'username' : username,
                       'password' : password }
        else:
            account = {'type' : account_type,
                       'username' : username,
                       'player_id' : player_id,
                       'password' : password }
        if mandatory:
            return account
        else:
            return util.purge_null_fields(account)

    def initialize(self):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

    def get_current_user(self):
        return self.get_secure_cookie('user')

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/login', permanent = True)

class LoginHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/date')
        else:
            self.render('login.html')

    def post(self):
        # TODO: check the password here
        self.set_secure_cookie('user', self.get_argument('name'))
        self.redirect('/date')

class LogoutHandler(DynamicBaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/login')

class DateHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            name = tornado.escape.xhtml_escape(self.current_user)
        else:
            name = 'nobody'
        self.render('date.html',
                    date_string = str(datetime.datetime.now()),
                    user_string = name)

class AddPlayerHandler(DynamicBaseHandler):

    # TODO: this is a placeholders until we bring up the database backend
    def update_database(self, player):
        # REVISIT: real player ID will be generated by the database
        #          once we get the backend in place
        player_id = 42
        player.update({'player_id': player_id})
        return True

    def get(self):
        args = self.get_args()
        if args == None:
            return
        player = self.get_player_args(args, True)
        if player == None:
            return
        if self.update_database(player):
            self.finish_success(player)
        else:
            self.finish_failure("could not add player to the database")

class DelPlayerHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        # TODO: remove the entry from the database
        self.finish_success({'player_id': player_id})

class UpdatePlayerHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        player = self.get_player_args(args, False)
        if player == None:
            return
        try:
            player_id = int(args['player_id'][0])
        except:
            self.finish_failure("missing or invalid player ID")
            return
        player.update({'player_id': player_id})
        # REVISIT: update player record in the database
        self.finish_success(player)

class GetPlayerHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        # everything is optional except an empty set
        player = self.get_player_args(args, False)
        if player == None:
            player = {}
        try:
            player_id = int(args['player_id'][0])
        except:
            player_id = None
        if player_id:
            player.update({'player_id': player_id})
        if not player:
            self.finish_failure("must specify at least one search key")
            return
        try:
            op = args['op'][0].lower()
        except:
            op = 'and'
        if not op:
            op = 'and'
        elif op != 'and' and op != 'or':
            self.finish_failure("invalid search operator")
            return
        _log.info("get_player: search operator is '{}'".format(op))
        # TODO: database lookup comes here (use dictionary elements as keys
        #       and apply the specified operator
        self.finish_success(player)

class AddMatchHandler(DynamicBaseHandler):
    def update_database(self, match):
        # REVISIT: match_id will be generated by the database when we hook it up
        match_id = 42
        match.update({'match_id': match_id})
        return True

    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            challenger_id = int(args['challenger'][0])
        except:
            self.finish_failure("challenger ID missing or invalid")
            return
        try:
            opponent_id = int(args['opponent'][0])
        except:
            self.finish_failure("opponent ID missing or invalid")
            return
        try:
            cgames_str = args['cgames']
            cgames = [ int(g) for g in cgames_str ]
        except:
            self.finish_failure("list of games won by challenger missing or invalid")
            return
        try:
            ogames_str = args['ogames']
            ogames = [ int(g) for g in ogames_str ]
        except:
            self.finish_failure("list of games won by opponent missing or invalid")
            return
        try:
            forfeited = util.str_to_bool(args['forfeited'][0])
            if forfeited == None:
                self.finish_failure("forfeited-flag must be boolean")
                return
        except:
            forfeited = False
        try:
            retired = util.str_to_bool(args['retired'][0])
            if retired == None:
                self.finish_failure("retired-flag must be boolean")
                return
        except:
            retired = False
        try:
            tournament = util.str_to_bool(args['tournament'][0])
            if tournament == None:
                self.finish_failure("tournament-flag must be boolean")
                return
        except:
            tournament = False
        try:
            date = datetime.strptime(args['date'][0], '%Y-%m-%d')
        except:
            self.finish_failure("match date missing")
            return
        winner_id, cpoints, opoints, err = rules.process_match(challenger_id, opponent_id, cgames, ogames, retired, forfeited, date, tournament)
        if err:
            self.finish_failure(err)
            return
        match = {'opponent_id': opponent_id,
                 'challenger_id': challenger_id,
                 'winner_id': winner_id,
                 'cgames': cgames,
                 'ogames': ogames,
                 'cpoints': cpoints,
                 'opoints': opoints,
                 'retired': retired,
                 'forfeited' : forfeited,
                 'date': str(date).split()[0],
                 'tournament': tournament}
        # TODO: we also need to do the following along with adding
        #       the match to the database:
        # 1) promote the player if applicable
        # 2) record the match ID that promoted the player to the current ladder
        # 3) record the ladder from which the player came from (so that we can
        #    demote him/her if the promoting match has been deleted
        # All of the above must be done in transactional manner so that we don't
        # end up with inconsistent records if something crashes in the middle
        # of the transaction
        if self.update_database(match):
            self.finish_success(match)
        else:
            self.finish_failure("could not add match to the database")

class DelMatchHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            match_id = int(args['match_id'][0])
        except:
            self.finish_failure("missing or invalid match ID")
            return
        # TODO: remove the entry from the database
        # don't forget that if we are deleting a match that promoted
        # a player, that the player must be demoted to the rank it came from
        self.finish_success({'match_id': match_id})

class GetMatchHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            players  = args['player']
            if len(players) > 2:
                self.finish_failure("cannot have more than two players")
                return
        except:
            players = None
        try:
            date = datetime.strptime(args['date'][0], '%Y-%m-%d')
        except:
            date = None
        keys =  util.purge_null_fields({ 'players': players,
                                         'date': str(date).split()[0] if date else None })
        # TODO: lookup match here
        if keys:
            self.finish_success(keys)
        else:
            self.finish_failure("no valid keys specified")

class AddAccountHandler(DynamicBaseHandler):
    def update_database(self, account):
        # TODO: will be generated by the database
        account_id = 42
        account.update({'account_id': account_id})
        return True

    def get(self):
        args = self.get_args()
        if args == None:
            return
        account = self.get_account_args(args, True)
        if account == None:
            return
        # TODO: check that the username is not in use
                # TODO: check if a player has already been associated with an account
        if self.update_database(account):
            self.finish_success(account)
        else:
            self.finish_failure("could not add account to database")

class DelAccountHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            account_id = int(args['account_id'][0])
        except:
            self.finish_failure("missing or invalid account ID")
            return
        # TODO: remove the entry from the database
        self.finish_success({'account_id': account_id})

class GetAccountHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        # everything is optional except an empty set
        account = self.get_account_args(args, False)
        if account == None:
            account = {}
        try:
            account_id = int(args['account_id'][0])
        except:
            account_id = None
        if account_id:
            account.update({'account_id': account_id})
        if not account:
            self.finish_failure("must specify at least one search key")
            return
        # TODO: database lookup comes here (use dictionary elements as keys
        #       and apply the specified operator)
        self.finish_success(account)

class GetReportHandler(DynamicBaseHandler):
    def get(self):
        args = self.get_args()
        if args == None:
            return
        try:
            latest = util.str_to_bool(args['latest'][0])
            if latest == None:
                latest = True
        except:
            latest = False
        if latest:
            # latest report spans two most recent report days
            dates =  [ datetime.now() - timedelta(i) for i in range(0, 14) if (datetime.now() - timedelta(i)).weekday() == rules.report_day() ]
            until = dates[0]
            since = dates[1]
        else:
            try:
                since = datetime.strptime(args['since'][0], '%Y-%m-%d')
            except:
                self.finish_failure("must specify the report start date")
                return
            try:
                until = datetime.strptime(args['until'][0], '%Y-%m-%d')
            except:
                until = datetime.now()
        ranges = {'since' : str(since).split()[0],
                  'until' : str(until).split()[0]}
        # TODO: do the series of database reads and construct the report
        self.finish_success(ranges)

def run_server(ssl_options = _test_ssl_options, http_port = 80, https_port = 443, html_root = sys.prefix + '/var/jim/html', template_root = sys.prefix + '/var/jim/templates'):
    global _http_server
    global _https_server
    global _log

    # if some bozo calls us with None specified as an argument
    if template_root == None:
        template_root = sys.prefix + '/var/jim/templates'
    if html_root == None:
        html_root = sys.prefix + '/var/jim/html'

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/login', LoginHandler),
        ('/logout', LogoutHandler),
        ('/date', DateHandler),
        ('/add_player', AddPlayerHandler),
        ('/del_player', DelPlayerHandler),
        ('/get_player', GetPlayerHandler),
        ('/update_player', UpdatePlayerHandler),
        ('/add_match', AddMatchHandler),
        ('/del_match', DelMatchHandler),
        ('/get_match', GetMatchHandler),
        ('/add_account', AddAccountHandler),
        ('/del_account', DelAccountHandler),
        ('/get_account', GetAccountHandler),
        ('/get_report', GetReportHandler)
        ]

    _log = logging.getLogger("web")
    handlers.append(('/(.*)', web.StaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers = handlers, template_path = template_root,
                                  cookie_secret = binascii.b2a_hex(os.urandom(32)))
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
