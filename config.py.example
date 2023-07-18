#!/usr/bin/python
# -*- coding: UTF8 -*-

API_URL = "https://feddit.de"
USERNAME = "BOT NAME"
PASSWORD = "BOT PASSWORD"
RATE_LIMIT_SECONDS = 0
CHECK_INTERVAL_SECONDS = 60

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