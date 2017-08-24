# coding: utf-8

from datetime import datetime
from slackbot.bot import Bot

def main():
    b = Bot()
    b.run()

if __name__ == '__main__':
    print(datetime.today(), 'start slackbot')
    main()

