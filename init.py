# coding: utf-8

import sqlite3
from privatedata import DB # DB file name

# journal
with sqlite3.connect(DB) as con:
    cur=con.cursor()
    cur.execute('drop table if exists account')
    # 自動採番するには int ではなく integer でないとダメ
    cur.execute('''create table account (
    aname varchar(255) unique
    )''')
    cur.execute('drop table if exists journal')
    cur.execute('''create table journal (
    transaction_id int unsigned,
    deal_date date,
    acode int unsigned,
    price int,
    side tinyint unsigned,
    description text
    );''')
    con.commit()

