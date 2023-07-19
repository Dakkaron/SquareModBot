#!/usr/bin/python
# -*- coding: UTF8 -*-

from pythorhead import Lemmy

print("This script gives a target bot moderator rights on a target community,")
print("without the bot having to post there first.")
if input("Are you sure you want to do that? (y/N)").strip() not in ["y","Y"]:
	print("Aborting")
	exit()
instanceUrl = input("Instance URL:   ")
currentUser = input("Your user name: ")
currentPass = input("Your password:  ")
botName     = input("Bot user name:  ")
community   = input("Community name: ")

print()
print(f"Instance URL:    {instanceUrl}")
print(f"Your user name:  {currentUser}")
print(f"Your password:   {currentPass}")
print(f"Bot user name:   {botName}")
print(f"Community name:  {community}")

if input("Is everything correct? (y/N)").strip() not in ["y","Y"]:
	print("Aborting")
	exit()

lemmy = Lemmy(instanceUrl)
lemmy.login(currentUser, currentPassword)

communityId = lemmy.community.get(name = community)["community_view"]["community"]["id"]
personId = lemmy.user.get(username = botName)["person_view"]["person"]["id"]

lemmy.community.add_mod_to_community(added = True, communityId = communityId, personId = personId)