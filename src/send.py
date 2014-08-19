# -*- coding: utf- -*-
import json
from grab import Grab


class ProblemsSender(object):

    def __init__(self, admin_host, admin_login, admin_pass):
        self.admin_host = admin_host
        self.admin_login = admin_login
        self.admin_pass = admin_pass

    def send(self, problemModel):
        modelJson = json.dumps(problemModel)
        g = Grab(log_dir='logs/server/')
        # Выполним аутентификацию
        g.setup(post={'j_username': self.admin_login, 'j_password':
                self.admin_pass})
        g.go(self.admin_host + "/sign-in")

        # Отправим маршрут на сервер
        g.setup(post=modelJson, headers = {'Content-Type' : 'application/json'})
       
        g.go(self.admin_host + "/problems/insertSharedProblem.json")
