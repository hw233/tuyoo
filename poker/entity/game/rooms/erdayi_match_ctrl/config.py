# -*- coding: utf-8 -*-
"""
Created on 2014年9月23日

@author: zjgzzz@126.com
"""
from datetime import datetime
from sre_compile import isstring
import time
from freetime.util.cron import FTCron
from poker.entity.biz.exceptions import TYBizConfException
from poker.entity.game.rooms.erdayi_match_ctrl.const import MatchType, FeeType, GroupingType, AnimationType, SeatQueuingType, MAX_CARD_COUNT
from poker.entity.game.rooms.erdayi_match_ctrl.exceptions import MatchConfException
import poker.util.timestamp as pktimestamp

class StartConfig(object, ):

    def __init__(self):
        pass

    def isTimingType(self):
        pass

    def isUserCountType(self):
        pass

    def calcNextStartTime(self, timestamp=None):
        pass

    def getTodayNextLater(self):
        pass

    def calcSigninTime(self, startTime):
        pass

    def calcPrepareTime(self, startTime):
        pass

    def buildSigninTimeStr(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def parse(cls, conf):
        pass

class GroupingConfig(object, ):

    def __init__(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def parse(cls, conf):
        pass

class StageConfig(object, ):

    def __init__(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def parse(cls, conf):
        pass

class RankRewards(object, ):

    def __init__(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def parse(cls, conf):
        pass

    @classmethod
    def buildRewardDescList(cls, rankRewardsList):
        pass

class TipsConfig(object, ):

    def __init__(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def parse(cls, conf):
        pass

class MatchFee(object, ):

    def __init__(self, assetKindId, count, params):
        pass

    def getParam(self, paramName, defVal=None):
        pass

    @property
    def failure(self):
        pass

    @classmethod
    def decodeFromDict(cls, d):
        pass

    def toDict(self):
        pass

class MatchConfig(object, ):
    VALID_GAMEIDS = [3, 6, 7, 15, 17, 21]

    def __init__(self):
        pass

    def checkValid(self):
        pass

    @classmethod
    def getTipsConfigClass(cls):
        pass

    @classmethod
    def getRankRewardsClass(cls):
        pass

    @classmethod
    def parse(cls, gameId, roomId, matchId, name, conf):
        pass