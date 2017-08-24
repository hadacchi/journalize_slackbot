# coding: utf-8

import datetime
import os
import re
import sqlite3
from slackbot.bot import respond_to
from slackbot.bot import listen_to
from slackbot.dispatcher import unicode_compact
from slackbot.dispatcher import Message
import sys
sys.path.append('..')
from privatedata import ch      # ch is dictionary from ch name to ch id
from privatedata import DB  # db filename
from privatedata import PID # path to pid file

__version__ = '0.2.0'
__author__  = 'hadacchi'


# aname pattern
apat = re.compile('(?P<val>\d+)$')
# option pattern
opat = re.compile(' (for|on) ')

pid  = os.getpid()
if os.path.isfile(PID):
    raise Exception('already started')
with open(PID,'w') as f:
    f.write(str(pid))

#@respond_to('mention', re.IGNORECASE)
#def menthion_func(message):
#    message.reply('mention')

#@listen_to('listen', re.IGNORECASE)
#def listen_func(message):
#    message.send('listen')
#    message.reply('reply')

@listen_to('^view')
def view(message):
    text = message.body['text']
    join = False
    if text.find(' ')<0:
        # show journal today
        date = datetime.date.today()
    else:
        _,dstr = text.split(' ',1)
        if dstr == 'T':
            # inner join account name
            join = True
            date = datetime.date.today()
        # for debug
        #elif dstr == 'message':
        #    message.send(str(dir(message)))
        #    return
        #elif dstr in dir(message):
        #    message.send(str(eval('dir(message.'+dstr+')')))
        #    return
        else:
            # parse date to show journal
            buf  = datetime.datetime.strptime(dstr,'%Y/%m/%d')
            date = buf.date()

    # open DB session
    db = kakeibohandler(DB)
    result = db.select_journal_by_date(date, join)
    message.send(str(result))

class myMessage(Message):
    @unicode_compact
    def send_to_channel(self, text, channel, thread_ts=None):
        self._client.rtm_send_message(channel, text, thread_ts=thread_ts)

@listen_to('^todo (.*)')
def send_to_todo(message, todo_str):
    mymsg = myMessage(message._client, message.body)
    mymsg.send_to_channel(todo_str, ch['todo'])

@listen_to('^from (.*) to (.*)')
def journal_insert(message, from_str, toopt_str):
    # parse message
    # accountとpriceのコンマ区切りは忘れそうなのでやめる
    flist = []
    for fstr in from_str.split(';'):
        mat = apat.search(fstr)
        acc = mat.string[:mat.start()]
        val = int(mat.group())
        flist.append((acc,val))

    buf = opat.split(toopt_str)
    to_str   = buf[0]
    desc_str = date = None
    if len(buf)>1:
        for v in zip(buf[1::2], buf[2::2]):
            if v[0] == 'for':
                desc_str = v[1]
            elif v[0] == 'on':
                x    = datetime.datetime.strptime(v[1],'%Y/%m/%d')
                date = x.date()

    tlist = []
    for tstr in to_str.split(';'):
        mat = apat.search(tstr)
        acc = mat.string[:mat.start()]
        val = int(mat.group())
        tlist.append((acc,val))

    if len(flist)<1 or len(tlist)<1:
        Exception('parse error')

    # open DB session
    db = kakeibohandler(DB)

    # insert DB
    tid = db.insert_journal(flist, tlist, desc_str, date)

    # show result
    message.reply(str(db.select_journal_by_tid(tid)), in_thread=True)

    #message.send('借方:{0}\n貸方:{1}'.format(str(flist),str(tlist)))
    #message.send(str(adict))

class kakeibohandler(object):
    INNERJOIN = 'inner join account on journal.acode = account.rowid'
    SELECTJOU = 'select * from journal'

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

    def insert_journal(self, flist, tlist, desc, date):
        # 重複排除のため集合内包を作ってからリスト化
        accs  = list({acc for acc,_ in flist + tlist})
        adict = self.get_acodes(accs)
        tid   = self.get_last_tid() + 1
        if date is None:
            today = datetime.date.today()
        else:
            today = date

        # check same record

        # insert journal
        elements = [(tid, today, adict[acc], val, 1, desc) for acc,val in flist] \
                + [(tid, today, adict[acc], val, 0, desc) for acc,val in tlist]
        self.cur.executemany('insert into journal values (?,?,?,?,?,?)', elements)
        self.con.commit()

        return tid

    def select_journal(self, optionstr='', optionparam=None):
        if not self.connected():
            self.connect(self.db)
        if optionparam is None:
            self.cur.execute(self.SELECTJOU)
        else:
            self.cur.execute(self.SELECTJOU + optionstr, optionparam)
            return self.cur.fetchall()

    def select_journal_by_tid(self, tid, join=False):
        return self.select_journal(' ' + (self.INNERJOIN if join else '') + ' where transaction_id=?', (tid,))

    def select_journal_by_date(self, date, join=False):
        return self.select_journal(' ' + (self.INNERJOIN if join else '') + ' where deal_date=?', (date,))

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

