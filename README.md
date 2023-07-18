# SquareModBot for Lemmy

This is a simple early access mod bot for Lemmy.

To run this, you need Python 3 and pythorhead. If you have pip installed, you can install pythorhead like so:

`pip install pythorhead`

After that you can run SquareModBot like this:

`python squareModBot.py`

## Configuring SquareModBot

Before running it, you need to configure SquareModBot.

First, open config.py and fill out these fields:

```
API_URL = "https://feddit.de"
USERNAME = "BOT NAME"
PASSWORD = "BOT PASSWORD"
```

You should always run the bot on the instance where the target community is hosted. Adjust the `API_URL` to reflect that.

Now the bot should be able to login.

Next you need to setup the communities, triggers and actions for the bot.

For that, fill out the dict in the variable `COMMUNITY_CONFIGS`:

```
COMMUNITY_CONFIGS = {
	"COMMUNITY NAME": {
		"triggers": [
			{
				"triggerType": "post_DuplicateUrl",
				"actions": [
					{
						"type": "postComment",
						"message": "This post has been locked because the linked URL is already discussed here: {existingPost[post][ap_id]}."
					},
					{
						"type": "lock",
						"value": True
					}
				]
			},
			{
				"triggerType": "post_Regex",
				"fields": ["url", "name", "body"],
				"regex": ".*reddit.*",
				"actions": [
					{
						"type": "remove",
						"value": True,
						"reason": "This post was removed because bad words aren't allowed here!"
					}
				]
			}
		]
	}
}
```

You need to put the name of the community as the key of the values in `COMMUNITY_CONFIGS`. In the current example, the community that is managed is called `"COMMUNITY NAME"`. One instance of SquareBotMod can moderate multiple communities, so you can add more communities to the dict if you want to.

Next, each community has a list of triggers. Each trigger has a `triggerType` that determines what the trigger reacts to. The currently available `triggerType`s are:

- `post_DuplicateUrl`: Triggers whenever a new post is created that has the same URL as an already existing post in the same community.
- `post_Regex`: Triggers whenever a new post is created that matches a given regex. It will run the `regex` against the values of the fields in the post defined by what's in `fields`.

When a trigger is triggered, its `actions` will get executed from top to bottom. Currently these actions are available:

- `postComment`: Creates a comment to the post. The content of the comment will be the `message`.
- `lock`: Locks or unlocks the post. (`"value": True` means lock, `"value": False` means unlock)
- `remove`: Removes or restores the post. (`"value": True` means remove, `"value": False means restore, `"reason"` contains the reason that is given in the modlog)
