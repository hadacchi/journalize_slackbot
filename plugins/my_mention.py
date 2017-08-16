# coding: utf-8

import datetime
import os
import re
import sqlite3
from slackbot.bot import respond_to
from slackbot.bot import listen_to

__version__ = '0.1.0'
__author__  = 'hadacchi'

apat = re.compile('(?P<val>\d+)$')
pid  = os.getpid()
with open('run.pid','w') as f:
    f.write(str(pid))

#@respond_to('mention', re.IGNORECASE)
#def menthion_func(message):
#    message.reply('mention')

#@listen_to('listen', re.IGNORECASE)
#def listen_func(message):
#    message.send('listen')
#    message.reply('reply')

@respond_to('from (.*) to (.*)')
def journal_insert(message, from_str, todesc_str):
    # parse message
    # accountとpriceのコンマ区切りは忘れそうなのでやめる
    flist = []
    for fstr in from_str.split(';'):
        mat = apat.search(fstr)
        acc = mat.string[:mat.start()]
        val = int(mat.group())
        flist.append((acc,val))

    if todesc_str.find(' for ')>0:
        to_str, desc_str = todesc_str.split(' for ',1)
    else:
        to_str   = todesc_str
        desc_str = None

    tlist = []
    for tstr in to_str.split(';'):
        mat = apat.search(tstr)
        acc = mat.string[:mat.start()]
        val = int(mat.group())
        tlist.append((acc,val))

    if len(flist)<1 or len(tlist)<1:
        Exception('parse error')

    # open DB session
    db = kakeibohandler('kakeibo.db')

    # insert DB
    tid = db.insert_journal(flist, tlist, desc_str)

    # show result
    message.send(str(db.select_journal_by_tid(tid)))

    #message.send('借方:{0}\n貸方:{1}'.format(str(flist),str(tlist)))
    #message.send(str(adict))

class kakeibohandler(object):
    def __init__(self, fname):
        self.con = None
        self.cur = None
        self.db  = fname

    def connect(self, fname):
        self.con = sqlite3.connect(fname)
        self.cur = self.con.cursor()

    def connected(self):
        if self.con is None:
            return False
        return True

    def __del__(self):
        self.con.close()

    # journal handling
    def get_last_tid(self):
        if not self.connected():
            self.connect(self.db)
        self.cur.execute('select transaction_id from journal order by rowid desc limit 1')
        buf = self.cur.fetchone()
        if buf is None:
            return 0
        else:
            return buf[0]

    def insert_journal(self, flist, tlist, desc):
        # 重複排除のため集合内包を作ってからリスト化
        accs  = list({acc for acc,_ in flist + tlist})
        adict = self.get_acodes(accs)
        tid   = self.get_last_tid() + 1
        today = datetime.date.today()

        # check same record

        # insert journal
        elements = [(tid, today, adict[acc], val, 1, desc) for acc,val in flist] \
                + [(tid, today, adict[acc], val, 0, desc) for acc,val in tlist]
        self.cur.executemany('insert into journal values (?,?,?,?,?,?)', elements)
        self.con.commit()

        return tid

    def select_journal_by_tid(self, tid):
        if not self.connected():
            self.connect(self.db)
        self.cur.execute('select * from journal where transaction_id=?',(tid,))
        return self.cur.fetchall()

    # account handling
    def acc_exists(self, aname):
        if not self.connected():
            self.connect(self.db)
        self.cur.execute('select rowid from account where aname=? limit 1',(aname,))
        if self.cur.fetchone() is None:
            return False
        else:
            return True

    def insert_accs(self, anames):
        if not self.connected():
            self.connect(self.db)
        self.cur.executemany('insert into account values (?)', anames)
        self.con.commit()

    def get_acodes(self, anames):
        newnames = [(aname,) for aname in anames if not self.acc_exists(aname)]
        if len(newnames)>0:
            self.insert_accs(newnames)
        self.cur.execute(
                'select *,rowid from account where {0}'.format(
                    ' or '.join(['aname=?']*len(anames))
                    ),
                anames
                )
        return dict(self.cur.fetchall())

