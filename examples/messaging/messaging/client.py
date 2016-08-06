import threading
import requests
from requests import Request, Session
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests import RequestException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import json
import time
import curses

_SERVER = 'http://localhost:6543'

def post(message, token):
    data = {'text': message}
    s = Session()
    req = Request('POST', _SERVER, json=data)
    prepped = s.prepare_request(req)
    prepped.headers['X-Messaging-Token'] = token
    resp = s.send(prepped)

def register(name):
    url = _SERVER + '/users'
    try:
        s = Session()
        req = Request('POST', url, data=name)
        prepped = s.prepare_request(req)    
        resp = s.send(prepped)
    except RequestException:
        return False

    if resp.status_code != 200:
        return False

    return json.loads(resp.text)['token']

class UpdateThread(threading.Thread):
    def __init__(self, server, token, scr):
        threading.Thread.__init__(self)
        self.server = server
        self.token = token
        self.updating = False
        self.pause = 1
        self.scr = scr

    def run(self):
        self.updating = True
        s = Session()
        req = Request('GET', self.server)
        prepped = s.prepare_request(req)
        prepped.headers['X-Messaging-Token'] = self.token
        resp = s.send(prepped)

        while self.updating:
            r = s.get(self.server)
            result = json.loads(resp.text)
            if result == []:
                continue

            y, x = self.scr.getyx()
            for index, line in enumerate(reversed(result)):
                self.scr.addstr(index + 2, 0,
                        '%s> %s' % (line['user'], line['text']))
            self.scr.move(y, x)
            self.scr.addstr(y, x, '')
            self.scr.refresh()
            time.sleep(self.pause)

    def stop(self):
        self.updating = False
        self.join()


def get_str(y, x, screen, msg):
    screen.addstr(y, x,  msg)
    str = []
    while True:
        cchar = screen.getch()
        if cchar == 10:
            return ''.join(str)
        str.append(chr(cchar))


def shell():
    stdscr = curses.initscr()
    stdscr.addstr(0, 0, "Welcome (type 'exit' to exit)")
    token = None

    while token is None:
        name = get_str(1, 0, stdscr, 'Select a name : ')
        token = register(name)
        if token is None:
            print('That name is taken')

    update = UpdateThread(_SERVER, token, stdscr)
    update.start()
    while True:
        try:
            msg = get_str(10, 0, stdscr, '> ')
            if msg == 'exit':
                break
            else:
                post(msg, token)

            stdscr.addstr(10, 0, ' ' * 100)
        except KeyboardInterrupt:
            update.stop()

    curses.endwin()

if __name__ == '__main__':
    shell()


