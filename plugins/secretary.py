# coding: utf-8

import datetime
import io
import os
import re
import sqlite3
from texttables.dynamic import writer as tblwriter
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

# strptime で使う文字列
dfmt = {
        8: '%Y%m%d',
        6: '%y%m%d',
        4: '%m%d',
        }
# re で使う文字列．セパレータが-とか:とか/とか揺れてても吸収する
spat = '[^\d]*(?P<m>\d{1,2}).(?P<d>\d{1,2})[^\d]*'              #  3-5 chars    1/1 - 12/31
mpat = '[^\d]*(?P<y>\d{2}).(?P<m>\d{1,2}).(?P<d>\d{1,2})[^\d]*' #  6-8 chars 17/1/1 - 17/12/31
lpat = '[^\d]*(?P<y>\d{4}).(?P<m>\d{1,2}).(?P<d>\d{1,2})[^\d]*' # 8-10 chars 2017/1/1 - 2017/12/31

def dstrtodt(dstr):
    '色々なパターンの日付文字列をdatetimeオブジェクトにして返す'
    # セパレータの有無を判定
    if len(re.sub('\d','',dstr))>0:
        # セパレータがある場合のマッチング文字列の場合分け
        if len(dstr) <6:
            pats = [spat,]
        elif len(dstr)<8:
            pats = [mpat,]
        elif len(dstr)==8:
            pats = [mpat,lpat,]
        elif len(dstr)<11:
            pats = [lpat,]
        else:
            pats = []

        for p in pats:
            cpat = re.compile(p)
            mat  = cpat.search(dstr)
            if mat:
                # 数字のみ連結
                nstr = ''.join(map(lambda x: '{0:02d}'.format(int(x)), mat.groups()))
                break
        else:
            # for の else. マッチする文字列なし
            raise Exception('invalid date format')
    else:
        # 全部数字
        nstr = dstr
    if len(nstr) in dfmt:
        now = datetime.datetime.today()
        t = datetime.datetime.strptime(nstr, dfmt[len(nstr)])
        if len(nstr)<5:
            t = t.replace(year=now.year)
    else:
        raise Exception('invalid data format')
    return t

@listen_to('^view')
def view(message):
    '情報をチャットに書き出す'
    text = message.body['text']
    join = False
    date = datetime.date.today()
    if text.find(' ')>0:
        dstrlist= text.split(' ')
        for dstr in dstrlist[1:]:
            if dstr == 'T':
                # inner join account name
                join = True
            elif dstr == 'account':
                db = kakeibohandler(DB)
                message.send(str(db.get_accounts()))
                return
            # for debug
            #elif dstr == 'message':
            #    message.send(str(dir(message)))
            #    return
            #elif dstr in dir(message):
            #    message.send(str(eval('dir(message.'+dstr+')')))
            #    return
            else:
                # parse date to show journal
                buf  = dstrtodt(dstr)
                #buf  = datetime.datetime.strptime(dstr,'%Y/%m/%d')
                date = buf.date()

    # open DB session
    db = kakeibohandler(DB)
    result = db.select_journal_by_date(date, True)
    'result is  tid, date, acode, price, LorR, desc, aname'
    'fields are tid, date, account, price L, price R, desc'
    data   = [list(map(str,[
                            r[0],
                            r[1],
                            r[-1],
                            '' if r[4] else r[3],
                            r[3] if r[4] else '',
                            r[5]
                            ])) for r in result]
    buf = io.StringIO()
    #message.send(str(data))
    #with tblwriter(buf, ['','','','','','']) as wobj:
    with tblwriter(buf, ['>','<','<','>','>','<']) as wobj:
        wobj.writeheader(['', 'date', 'account', 'price LHS', 'price RHS', 'description'])
        wobj.writerows(data)

    out = '```'
    out += buf.getvalue()
    out += '```'
    message.send(out)

class myMessage(Message):
    '''slackbotのMessageクラスは他のチャットに書き出せないので
    チャネルを指定して書き出すためのメソッドを追加した継承クラスを作った
    '''
    @unicode_compact
    def send_to_channel(self, text, channel, thread_ts=None):
        self._client.rtm_send_message(channel, text, thread_ts=thread_ts)

@listen_to('^todo (.*)')
def send_to_todo(message, todo_str):
    'todo チャネルにメッセージを転記する'
    mymsg = myMessage(message._client, message.body)
    mymsg.send_to_channel(todo_str, ch['todo'])

@listen_to('^from (.*) to (.*)')
def journal_insert(message, from_str, toopt_str):
    '仕訳情報を展開して仕訳DBに追記する'
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
                #x    = datetime.datetime.strptime(v[1],'%Y/%m/%d')
                x    = dstrtodt(v[1])
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


class kakeibohandler(object):
    '仕訳DB，勘定科目DBの操作をまとめたクラス'
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
        return self.select_journal(' ' + (self.INNERJOIN if join else '') + ' where deal_date=? order by deal_date, transaction_id, side', (date,))

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

    def get_accounts(self):
        if not self.connected():
            self.connect(self.db)
        self.cur.execute('select aname,rowid from account')
        return dict(self.cur.fetchall())

