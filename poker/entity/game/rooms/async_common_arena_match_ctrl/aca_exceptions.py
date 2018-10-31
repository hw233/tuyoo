# -*- coding: utf-8 -*-
"""
Created on 2017年10月13日

@author: zhaol

"""

class AsyncCommonArenaError(object, ):
    NO_MATCH = '\xe6\xb2\xa1\xe6\x9c\x89\xe8\xbf\x99\xe4\xb8\xaa\xe6\xaf\x94\xe8\xb5\x9b\xef\xbc\x8c\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95'
    MATCH_NOT_START = '\xe6\xaf\x94\xe8\xb5\x9b\xe5\xb0\x9a\xe6\x9c\xaa\xe5\xbc\x80\xe5\x90\xaf\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe5\x86\x8d\xe6\x9d\xa5'
    MATCH_ENDING = '\xe6\xaf\x94\xe8\xb5\x9b\xe9\xa9\xac\xe4\xb8\x8a\xe7\xbb\x93\xe6\x9d\x9f\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe5\x86\x8d\xe6\x9d\xa5'
    MATCH_ENDED = '\xe6\xaf\x94\xe8\xb5\x9b\xe5\xb7\xb2\xe7\xbb\x8f\xe7\xbb\x93\xe6\x9d\x9f\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe5\x86\x8d\xe6\x9d\xa5'
    COIN_TOO_MUCH = '\xe6\x82\xa8\xe5\xb7\xb2\xe7\xbb\x8f\xe6\x98\xaf\xe9\xab\x98\xe6\x89\x8b\xe4\xba\x86\xef\xbc\x8c\xe8\xaf\xb7\xe8\xbf\x9b\xe5\x85\xa5\xe6\x9b\xb4\xe9\xab\x98\xe7\x9a\x84\xe6\xaf\x94\xe8\xb5\x9b'
    COIN_TOO_LESS = '\xe6\x82\xa8\xe7\x9a\x84\xe9\x87\x91\xe5\xb8\x81\xe4\xb8\x8d\xe8\xb6\xb3\xef\xbc\x8c\xe8\xaf\xb7\xe8\xb5\xa2\xe5\xa4\x9f\xe9\x87\x91\xe5\xb8\x81\xe5\x90\x8e\xe6\x8a\xa5\xe5\x90\x8d\xe6\xaf\x94\xe8\xb5\x9b'
    FEE_NOT_ENOUGH = '\xe8\xb4\xb9\xe7\x94\xa8\xe4\xb8\x8d\xe8\xb6\xb3\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe5\x86\x8d\xe6\x9d\xa5'
    NOT_IN_MATCH = '\xe6\x82\xa8\xe4\xb8\x8d\xe5\x9c\xa8\xe6\xaf\x94\xe8\xb5\x9b\xe4\xb8\xad'
    MATCH_ALREADY_STARTED = '\xe6\xaf\x94\xe8\xb5\x9b\xe5\xb7\xb2\xe7\xbb\x8f\xe5\xbc\x80\xe5\xa7\x8b\xef\xbc\x8c\xe5\xa6\x82\xe9\x9c\x80\xe9\x80\x80\xe5\x87\xba\xe8\xaf\xb7\xe9\x80\x89\xe6\x8b\xa9\xe6\x94\xbe\xe5\xbc\x83\xe6\xaf\x94\xe8\xb5\x9b'
    ALREADY_IN_MATCH = '\xe6\x82\xa8\xe5\xb7\xb2\xe7\xbb\x8f\xe5\x9c\xa8\xe6\xaf\x94\xe8\xb5\x9b\xe4\xb8\xad\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe6\x8a\xa5\xe5\x90\x8d'
    ALREADY_IN_GIVEUP_MATCH = '\xe6\x82\xa8\xe9\x80\x80\xe8\xb5\x9b\xe7\x9a\x84\xe6\xaf\x94\xe8\xb5\x9b\xe8\xbf\x98\xe5\x9c\xa8\xe8\xbf\x9b\xe8\xa1\x8c\xe4\xb8\xad\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe6\x8a\xa5\xe5\x90\x8d'
    STATE_NOT_WAIT_CHALLENGE = '\xe6\x82\xa8\xe7\x9a\x84\xe6\xaf\x94\xe8\xb5\x9b\xe4\xb8\x8d\xe6\xbb\xa1\xe8\xb6\xb3\xe7\xbb\xa7\xe7\xbb\xad\xe7\x9a\x84\xe6\x9d\xa1\xe4\xbb\xb6'
    STATE_NOT_WAIT_REVIVE = '\xe6\x82\xa8\xe7\x9a\x84\xe6\xaf\x94\xe8\xb5\x9b\xe4\xb8\x8d\xe6\xbb\xa1\xe8\xb6\xb3\xe5\xa4\x8d\xe6\xb4\xbb\xe7\x9a\x84\xe6\x9d\xa1\xe4\xbb\xb6'
    CANNOT_SAVE = '\xe5\xbd\x93\xe5\x89\x8d\xe4\xb8\x8d\xe5\x8f\xaf\xe4\xbf\x9d\xe5\xad\x98\xe8\xbf\x9b\xe5\xba\xa6'
    IN_OTHER_MATCH = '\xe6\x82\xa8\xe6\xad\xa3\xe5\x9c\xa8\xe5\x85\xb6\xe4\xbb\x96\xe7\x8e\xa9\xe6\xb3\x95/\xe6\xaf\x94\xe8\xb5\x9b\xe4\xb8\xad\xef\xbc\x8c\xe8\xaf\xb7\xe7\xa8\x8d\xe5\x90\x8e\xe6\x8a\xa5\xe5\x90\x8d'