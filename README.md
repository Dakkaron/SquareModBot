# SquareModBot for Lemmy

This is a simple early access mod bot for Lemmy.

To run this, you need Python 3 and pythorhead. If you have pip installed, you can install pythorhead like so:

`pip install pythorhead`

After that you can run SquareModBot like this:

`python squareModBot.py`

## Configuring SquareModBot

Before running it, you need to configure SquareModBot.

First, copy config.py.example to config.py, open config.py and fill out these fields:

```
API_URL = "https://feddit.de"
USERNAME = "BOT NAME"
PASSWORD = "BOT PASSWORD"
```

You should always run the bot on the instance where the target community is hosted. Adjust the `API_URL` to reflect that.

Now the bot should be able to login.

Next you need to setup the communities, triggers and actions for the bot.

For that, copy `communityConfig.json.example` to `communityConfig.json` and edit it:

```
{
	"COMMUNITY NAME": {
		"triggers": [
			{
				"triggerType": "post_DuplicateUrl",
				"actions": [
					{
						"type": "postComment",
						"content": "This post has been locked because the linked URL is already discussed here: {existingPost.post.ap_id}."
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

You need to put the name of the community as the key of the values in the top level dict. In the current example, the community that is managed is called `"COMMUNITY NAME"`. One instance of SquareBotMod can moderate multiple communities, so you can add more communities to the dict if you want to.

Next, each community has a list of triggers. Each trigger has a `triggerType` that determines what the trigger reacts to. The currently available `triggerType`s are:

- `post_DuplicateUrl`: Triggers whenever a new post is created that has the same URL as an already existing post in the same community.
- `post_Regex`: Triggers whenever a new post is created that matches a given regex. It will run the `regex` against the values of the fields in the post defined by what's in `fields`.
- `comment_Regex`: Triggers whenever a new comment is created that matches a given regex. It will run the `regex` only against the comment's text content.

When a trigger is triggered, its `actions` will get executed from top to bottom. Currently these actions are available:

- `postComment`: Creates a comment to the matching post/comment. The content of the comment will be the `message`.
- `remove`: Removes or restores the post/comment. (`"value": True` means remove, `"value": False means restore, `"reason"` contains the reason that is given in the modlog)
- `lock`: (Posts only) Locks or unlocks the post. (`"value": True` means lock, `"value": False` means unlock)

The fields `content` and `reason` can use Python's string formatting to inject values from the affected posts/comments.

For posts the target post (and in case of `post_DuplicateUrl`) the existing duplicate post are exposed as `targetPost` and `existingPost`. The same is done for comments with `targetComment`.
 
These data structures are the full post/comment object as returned by the API. To use the values of these fields in `content`/`reason`, put it in curly braces. To step into the object, use dots, like so:

```
"{targetPost.post.url}" -> returns the URL the post links to.
"{targetPost.post.name}" -> returns the title of the post.
"{targetPost.post.body}" -> returns the text of the post.
"{existingPost.post.ap_id}" -> returns the absolute URL to the post.
"{targetComment.comment.content}" -> returns the text of the comment.
```

### A note on Regexes

Bad regexes coupled with a fitting text input can lead to exponential run times. To avoid the bot getting stuck on evaluating such regexes, there is a maximum evaluation time limit in place. By default this is 0.2 seconds per regex call. You can adjust this limit using the variable `REGEX_TIME_LIMIT_SECONDS` in `config.py`.

Be careful to use fast and simple regexes if at all possible. Try to limit the usage of `+`and `*` as much as possible, and completely avoid nested `+` or `*`. For example, do not use regexes like this:

```
(a+)+b
```

So either use `+`/`*` inside or outside of a set of parenthesis, not both.

If the evaluation is interrupted due to it taking too long, the regex will not match and the post will not trigger any actions at all.