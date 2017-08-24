# coding: utf-8

import os
import signal
from privatedata import PID # pid file

if os.path.isfile(PID):
    with open(PID,'r') as f:
        pid = int(f.read())
    os.kill(pid, signal.SIGQUIT)
    os.remove(PID)
else:
    Exception('no run.pid file')
