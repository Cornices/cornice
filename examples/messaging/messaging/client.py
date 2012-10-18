import threading
import urllib2
import json
import time
import curses


_SERVER = 'http://localhost:6543'


def post(message, token):
    headers = {'X-Messaging-Token': token}
    req = urllib2.Request(_SERVER, headers=headers)
    req.get_method = lambda: 'POST'
    message = {'text': message}
    req.add_data(json.dumps(message))
    urllib2.urlopen(req)


def register(name):
    url = _SERVER + '/users'
    req = urllib2.Request(url)
    req.add_data(name)
    try:
        res = urllib2.urlopen(req)
    except urllib2.HTTPError:
        return False

    if res.getcode() != 200:
        return False

    return json.loads(res.read())['token']


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
        headers = {'X-Messaging-Token': self.token}
        req = urllib2.Request(self.server, headers=headers)

        while self.updating:
            res = urllib2.urlopen(req)
            result = json.loads(res.read())
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
