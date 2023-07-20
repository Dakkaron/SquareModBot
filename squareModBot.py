#!/usr/bin/python
# -*- coding: UTF8 -*-

from time import time, sleep
from pythorhead import Lemmy
from pythorhead.types.sort import SortType
from pythorhead.types.listing import ListingType
import re
import json
from timeout_decorator import timeout, TimeoutError

try:
	import config
except:
	print("ERROR: Configuration missing.")
	print("       Please copy config.py.example to config.py and adjust the configuration.")
	print("       Exiting now.")
	exit(1)

lemmy = None
communityConfig = {}
communityData = {}
MODBOT_USERID = 0


def templateString(template, data):
	output = ""
	inBracket = False
	bracketContent = ""
	for c in template:
		if inBracket:
			if c=="}":
				tokens = bracketContent.split(".")
				field = data[tokens.pop(0)]
				while tokens:
					field = field[tokens.pop(0)]
				output += str(field)
				bracketContent = ""
				inBracket = False
			else:
				bracketContent += c
		else:
			if c=="{":
				if output and output[-1]=="\\":
					output += c
				else:
					inBracket = True
			else:
				output += c
	return output

@timeout(seconds=config.REGEX_TIME_LIMIT_SECONDS)
def _reMatchTimeout(regex, string, flags, invertResult):
	if invertResult:
		return not re.match(regex, string, flags)
	else:
		return re.match(regex, string, flags)

def reMatchTimeout(regex, string, flags=0, invertResult=False):
	try:
		return _reMatchTimeout(regex, string, flags, invertResult)
	except TimeoutError:
		print("ERROR: Regex /{regex}/ timed out!")
		return None

def getNewComments(oldComments, printPageNr=False, community=None):
	oldCommentIds = [ x["comment"]["id"] for x in oldComments ]
	newComments = []
	current = [None]
	page = 0
	while current:
		page += 1
		if config.VERBOSE_MODE and printPageNr:
			print(f"Page: {page}")
		current = lemmy.comment.list(community_name=community, limit=50, page=page, sort=SortType.New, type_=ListingType.Subscribed)
		current = [ x for x in current if x["comment"]["creator_id"] != MODBOT_USERID ]
		newComments += [ x for x in current if x["comment"]["id"] not in oldCommentIds ]
		if any([ x for x in current if x["comment"]["id"] in oldCommentIds ]):
			break
		sleep(config.RATE_LIMIT_SECONDS)
	if config.VERBOSE_MODE:
		print(f"New comments found: {len(newComments)}")
	return newComments

def getPostUrlMap(allPosts):
	return { x["post"]["url"] : x for x in allPosts if "url" in x["post"] }

def isPostFeatured(post):
	return post["post"]["featured_community"] or post["post"]["featured_local"]

def getNewPosts(oldPosts, printPageNr=False, community=None):
	oldPostIds = [ x["post"]["id"] for x in oldPosts ]
	newPosts = []
	current = [None]
	page = 0
	while current:
		page += 1
		if config.VERBOSE_MODE and printPageNr:
			print(f"Page: {page}")
		current = lemmy.post.list(community_name=community, limit=50, page=page, sort=SortType.New, type_=ListingType.Subscribed)
		current = [ x for x in current if x["post"]["creator_id"] != MODBOT_USERID ]
		newPosts += [ x for x in current if x["post"]["id"] not in oldPostIds ]
		if any([ x for x in current if (not isPostFeatured(x)) and x["post"]["id"] in oldPostIds ]):
			break
		sleep(config.RATE_LIMIT_SECONDS)
	if config.VERBOSE_MODE:
		print(f"New posts found: {len(newPosts)}")
	return newPosts

def checkForNewDuplicatePosts(newPosts, oldPosts):
	urlMap = getPostUrlMap(oldPosts)
	return [ (x, urlMap[x["post"]["url"]]) for x in newPosts if "url" in x["post"] and x["post"]["url"] in urlMap ]

def checkPostTrigger(trigger, newPosts, oldPosts):
	actionSubjectList = []
	if trigger["triggerType"] == "post_DuplicateUrl":
		newDuplicates = checkForNewDuplicatePosts(newPosts, oldPosts)
		actionSubjectList = [{
				"targetPost" : x[0],
				"existingPost" : x[1]
			} for x in newDuplicates]
	elif trigger["triggerType"] == "post_Regex":
		actionSubjectList = [{
				"targetPost": x,
				"existingPost": x
			} for x in getPostsRegexMatch(trigger["regex"], newPosts, trigger["fields"], trigger.get("invert"))]
	return actionSubjectList

def executePostActions(trigger, actionSubjectList):
	for action in trigger["actions"]:
		for subject in actionSubjectList:
			if action["type"] == "postComment":
				content = templateString(action["content"], {"targetPost": subject["targetPost"], "existingPost": subject["existingPost"]})
				print(f"-> Creating comment: {content}")
				lemmy.comment.create(post_id = subject["targetPost"]["post"]["id"], content = content)
			elif action["type"] == "lock":
				postId = subject['targetPost']['post']['id']
				print(f"-> Locking post: {postId}")
				lemmy.post.lock(post_id = postId, locked = action.get("value", True))
			elif action["type"] == "remove":
				postId = subject['targetPost']['post']['id']
				reason = templateString(action["reason"], {"targetPost": subject["targetPost"], "existingPost": subject["existingPost"]})
				print(f"-> Removing post {postId} with the following reason: {reason}")
				lemmy.post.remove(post_id = postId, removed = action.get("value", True), reason = reason)

def checkCommentTrigger(trigger, newComments, oldComments):
	actionSubjectList = []
	if trigger["triggerType"] == "comment_Regex":
		actionSubjectList = [{
				"targetComment": x,
			} for x in newComments if reMatchTimeout(trigger["regex"], x["comment"]["content"], re.I, trigger.get("invert"))]
	return actionSubjectList

def executeCommentActions(trigger, actionSubjectList):
	for action in trigger["actions"]:
		for subject in actionSubjectList:
			commentId = subject['targetComment']['comment']['id']
			if action["type"] == "postComment":
				content = templateString(action["content"], {"targetComment": subject["targetComment"]})
				print(f"-> Creating comment: {content}")
				lemmy.comment.create(post_id = subject["targetComment"]["post"]["id"], parent_id = commentId, content = content)
			elif action["type"] == "remove":
				reason = templateString(action["reason"], {"targetComment": subject["targetPost"]})
				print(f"-> Removing comment {commentId} with the following reason: {reason}")
				lemmy.comment.remove(comment_id = commentId, removed = action.get("value", True), reason = reason)

def processTriggers(newPosts, newComments, communityData):
	for trigger in communityConfig[community]["triggers"]:
		if trigger["triggerType"].startswith("post_"):
			actionSubjectList = checkPostTrigger(trigger, newPosts, communityData[community]["oldPosts"])
			executePostActions(trigger, actionSubjectList)
		elif trigger["triggerType"].startswith("comment_"):
			actionSubjectList = checkCommentTrigger(trigger, newComments, communityData[community]["oldComments"])
			executeCommentActions(trigger, actionSubjectList)

def getPostsRegexMatch(regex, posts, fields, invertResult):
	out = []
	for post in posts:
		for field in fields:
			if field in post["post"] and reMatchTimeout(regex, post["post"][field], re.I, invertResult):
				out.append(post)
				break
	return out

def initializeCommunityData():
	global communityData, allOldPosts, allOldComments
	try:
		with open("communityDataCache.json", "r") as f:
			communityData = json.load(f)
			print("## Using cached community data")
	except:
		print("## Couldn't find cached community data, reading from API instead")
	for community in communityConfig:
		if community not in communityData:
			communityData[community] = {}
		if "oldPosts" not in communityData[community]:
			print(f"## Reading all existing posts in {community}")
			communityData[community]["oldPosts"] = getNewPosts([], True, community)
		if "oldComments" not in communityData[community]:
			print(f"## Reading all existing comments in {community}")
			communityData[community]["oldComments"] = getNewComments([], True, community)
	allOldPosts = sum([ communityData[x]["oldPosts"] for x in communityConfig ], [])
	allOldComments = sum([ communityData[x]["oldComments"] for x in communityConfig ], [])
	print("## Done reading posts/comments. Starting loop.\n")

def login():
	global lemmy
	lemmy = Lemmy(config.API_URL)
	if not lemmy.log_in(config.USERNAME, config.PASSWORD):
		print("ERROR: Login failed.")
		print("Exiting now")
		exit(1)

def checkModBotUserData():
	global MODBOT_USERID
	user = lemmy.user.get(username=config.USERNAME, limit=1)
	MODBOT_USERID = user["person_view"]["person"]["id"]
	for community in communityConfig:
		if community not in [ x["community"]["name"] for x in user["moderates"] ]:
			print(f"ERROR: {config.USERNAME} is not moderator in community {community}.")
			print("Exiting now.")
			exit(1)
	return user

def updateCommunitySubscriptions(userData):
	currentSubscriptions = [ x["community"]["id"] for x in lemmy.community.list(type_=ListingType.Subscribed) ]
	targetSubscriptions = [ x["community"]["id"] for x in userData["moderates"] ]
	needsSubscription = [ x for x in targetSubscriptions if x not in currentSubscriptions ]
	needsUnsubscription = [ x for x in currentSubscriptions if x not in targetSubscriptions ]
	for communityId in needsSubscription:
		lemmy.community.follow(id = communityId, follow = True)
	for communityId in needsUnsubscription:
		lemmy.community.follow(id = communityId, follow = False)

def splitPostsAndCommentsByCommunity(allNewPosts, allNewComments):
	newPostsByCommunity = {}
	newCommentsByCommunity = {}
	for community in communityConfig:
		newPostsByCommunity[community] = [ x for x in allNewPosts if x["community"]["name"] == community ]
		newCommentsByCommunity[community] = [ x for x in allNewComments if x["community"]["name"] == community ]
	return (newPostsByCommunity, newCommentsByCommunity)

def reloadCommunityConfig():
	global communityConfig
	if config.VERBOSE_MODE:
		print(f"## Reloading community config")
	text = None
	try:
		with open("communityConfig.json") as f:
			text = f.read()
	except:
		print("ERROR: Could not read communityConfig.json. Did you create it?")
		print("Exiting now")
		exit(1)
	try:
		communityConfig = json.loads(text)
	except:
		print("ERROR: communityConfig.json is not valid JSON. Please run it through a JSON validator.")
		print("Exiting now")
		exit(1)


if __name__ == "__main__":
	login()
	userData = checkModBotUserData()
	reloadCommunityConfig()
	updateCommunitySubscriptions(userData)
	initializeCommunityData()
	while True:
		print("## Start polling all communities")
		startTime = time()
		reloadCommunityConfig()
		allNewPosts = getNewPosts(allOldPosts)
		allNewComments = getNewComments(allOldComments)
		newPostsByCommunity, newCommentsByCommunity = splitPostsAndCommentsByCommunity(allNewPosts, allNewComments)
		for community in communityConfig:
			if config.VERBOSE_MODE:
				print(f"## Start processing community \"{community}\"")
			processTriggers(newPostsByCommunity[community], newCommentsByCommunity[community], communityData)
			communityData[community]["oldPosts"] += newPostsByCommunity[community]
			communityData[community]["oldComments"] += newCommentsByCommunity[community]
		allOldPosts += allNewPosts
		allOldComments += allNewComments
		if config.VERBOSE_MODE:
			print("## Finished polling all communities\n")
		if allNewPosts or allNewComments:
			if config.VERBOSE_MODE:
				print("## Updating community data cache\n")
			with open("communityDataCache.json", "w") as f:
				json.dump(communityData, f)
		sleep(max(0,config.CHECK_INTERVAL_SECONDS-(time()-startTime)))