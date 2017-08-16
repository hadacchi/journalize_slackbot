journalize_slackbot is a slackbot to journalize.

# requirements

- slack team
- server to work slackbot

# installation

1. make slack team for your journalization.
1. add Bot to your team's custom integrations.
1. setup your server to work this slackbot.
    1. install python3 and sqlite3.
    1. install slackbot via pip3.
    1. copy all files of this slackbot.
    1. go into a directory where you put the files.
    1. initialize DB by this command ```python3 init.py```.

# usage

1. start slackbot by this command

    python3 run.py

1. mention to your bot as follows

    @botname from {ACCOUNT_RHS}{PRICE};{ACCOUNT_RHS}{PRICE} to {ACCOUNT_LHS}{PRICE}{ACCOUNT_LHS}{PRICE} for {DESCRIPTION}

1. when you stop this slackbot, enter this command in the directory where the slackbot files are.

    python3 stop.py
