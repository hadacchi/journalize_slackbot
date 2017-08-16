# coding: utf-8

import os
import signal

if os.path.isfile('run.pid'):
    with open('run.pid','r') as f:
        pid = int(f.read())
    os.kill(pid, signal.SIGQUIT)
    os.remove('run.pid')
else:
    Exception('no run.pid file')
