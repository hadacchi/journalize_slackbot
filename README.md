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
    1. initialize DB by this command  
    ```python3 init.py```.

# usage

<ol>
    <li>
        start slackbot by this command
        <pre>python3 run.py</pre>
    </li>
    <li>
        mention to your bot as follows
        <pre>@botname from {ACCOUNT_RHS}{PRICE};{ACCOUNT_RHS}{PRICE} to {ACCOUNT_LHS}{PRICE}{ACCOUNT_LHS}{PRICE} for {DESCRIPTION}</pre>
        <ul>
            <li>for example,
                <pre>@botname from Cash100;TempPayment100 to OfficeSupply200 for notebook</pre>
            </li>
        </ul>
    </li>
    <li>
        when you stop this slackbot, enter this command in the directory where the slackbot files are.
        <pre>python3 stop.py</pre>
    </li>
</ol>

# tips

- account name cannot include number.
- pairs of account,price should be separated by \`;'.
- if a mention doesn't include \`for', description will be empty.
- no security, no encryption. you should guard your information by server security.
