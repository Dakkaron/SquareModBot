#!/usr/bin/python
# -*- coding: UTF8 -*-

from time import sleep
from pythorhead import Lemmy
from pythorhead.types.sort import SortType
import re
import config

communityData = {}

def getAllPostsOfCommunity(communityName):
	res = []
	page = 0
	current = [None]
	while current:
		page += 1
		print(f"Page: {page}")
		current = lemmy.post.list(community_name=communityName, limit=50, page=page, sort=SortType.New)
		res += current
		sleep(config.RATE_LIMIT_SECONDS)
	return res

def getPostUrlMap(allPosts):
	return { x["post"]["url"] : x for x in allPosts if "url" in x["post"] }

def isPostFeatured(post):
	return post["post"]["featured_community"] or post["post"]["featured_local"]

def getNewPosts(communityName, oldPosts):
	oldPostIds = [ x["post"]["id"] for x in oldPosts ]
	newPosts = []
	current = [None]
	page = 0
	while current:
		page += 1
		current = lemmy.post.list(community_name=communityName, limit=50, page=page, sort=SortType.New)
		newPosts += [ x for x in current if x["post"]["id"] not in oldPostIds ]
		if any([ x for x in current if (not isPostFeatured(x)) and x["post"]["id"] in oldPostIds ]):
			break
		sleep(config.RATE_LIMIT_SECONDS)
	print(f"New posts found: {len(newPosts)}")
	return newPosts

def checkForNewDuplicates(newPosts, oldPosts):
	urlMap = getPostUrlMap(oldPosts)
	return [ (x, urlMap[x["post"]["url"]]) for x in newPosts if "url" in x["post"] and x["post"]["url"] in urlMap ]

def checkTrigger(trigger, newPosts, oldPosts):
	actionSubjectList = []
	if trigger["triggerType"] == "post_DuplicateUrl":
		newDuplicates = checkForNewDuplicates(newPosts, oldPosts)
		actionSubjectList = [{
				"targetPost" : x[0],
				"existingPost" : x[1]
			} for x in newDuplicates]
	elif trigger["triggerType"] == "post_Regex":
		actionSubjectList = [{
				"targetPost": x,
				"existingPost": x
			} for x in getPostsRegexMatch(trigger["regex"], newPosts, trigger["fields"])]
	return actionSubjectList

def executeActions(trigger, actionSubjectList):
	for action in trigger["actions"]:
		for subject in actionSubjectList:
			if action["type"] == "postComment":
				messageText = action["message"].format(targetPost = subject["targetPost"], existingPost = subject["existingPost"])
				print(f"Creating message: {messageText}")
				lemmy.comment.create(post_id = subject["targetPost"]["post"]["id"], content = messageText)
			elif action["type"] == "lock":
				postId = subject['targetPost']['post']['id']
				print(f"Locking post: {postId}")
				lemmy.post.lock(post_id = postId, locked = action["value"])
			elif action["type"] == "remove":
				postId = subject['targetPost']['post']['id']
				print(f"Removing post: {postId}")
				lemmy.post.remove(post_id = postId, removed = action["value"], reason = action["reason"])

def processTriggers(newPosts, communityData):
	for trigger in config.COMMUNITY_CONFIGS[community]["triggers"]:
		actionSubjectList = checkTrigger(trigger, newPosts, communityData[community]["oldPosts"])
		executeActions(trigger, actionSubjectList)

def getPostsRegexMatch(regex, posts, fields):
	out = []
	for post in posts:
		for field in fields:
			if field in post["post"] and re.match(regex, post["post"][field], re.I):
				out.append(post)
				break
	return out

def initializeCommunities():
	for community in config.COMMUNITY_CONFIGS:
		print(f"## Reading all existing posts in {community}")
		communityData[community] = {}
		communityData[community]["oldPosts"] = getAllPostsOfCommunity(community)
	print("## Done reading posts. Starting loop.\n")

if __name__ == "__main__":
	lemmy = Lemmy(config.API_URL)
	if not lemmy.log_in(config.USERNAME, config.PASSWORD):
		print("Login failed. Exiting.")
		exit(1)
	initializeCommunities()
	while True:
		sleep(config.CHECK_INTERVAL_SECONDS)
		for community in config.COMMUNITY_CONFIGS:
			print(f"## Start polling community \"{community}\"")
			newPosts = getNewPosts(community, communityData[community]["oldPosts"])
			processTriggers(newPosts, communityData)
			communityData[community]["oldPosts"] += newPosts
		print("## Finished polling all communities\n")