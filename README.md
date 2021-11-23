### Start

* Issue a token from telegram BotFather
* Create .env with the token
* run the bot with `python botApp.py`

### Usage

* `\help` - halp
* `\init` - use on the very first run or if DB (just json file lol) is missing you
* `\list` - shows links you are currently watching
* `\add <NAME> <LINK>` - add name (keyword) and link to the list
* `\remove <NAME>` - remove a link from the list by it's keyword
* `\run` - start watching postings (querying every 5 minutes with random 1 minute delay)
* `\stop` - stop watching

Links can be removed and added while watching, no need to `stop`

On server restart all users will be restored and automatically start watching (aka
`\run` will be executed)

##### PS this is super buggy stuff and didn't mean to become anything
