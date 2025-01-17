# -*- coding:utf-8 -*-
'''
Created on 2018-06-14

@author: wangyonghui
'''
import json
import time

import datetime

import freetime.util.log as ftlog
import poker.util.timestamp as pktimestamp
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.segment.dao import segmentdata
from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper
from dizhu.game import TGDizhu
from dizhu.games.segmentmatch.events import SegmentRecoverEvent
from poker.entity.configure import configure
from poker.entity.dao import daobase


def isValidDatetime(dateTimeStr):
    ''' 2018-06-13  表示这是2018年6月13日凌晨4点到2018年6月14日凌晨4点有效的数据 '''
    try:
        startDateTime = datetime.datetime.strptime(dateTimeStr + ' 04:00:00', '%Y-%m-%d %H:%M:%S')
        endDateTime = startDateTime + datetime.timedelta(days=1)
        currentTimestamp = pktimestamp.getCurrentTimestamp()
        if time.mktime(startDateTime.timetuple()) <= currentTimestamp <= time.mktime(endDateTime.timetuple()):
            if ftlog.is_debug():
                ftlog.debug('user_share_behavior.isValidDatetime dateTimeStr=', dateTimeStr, 'ret=', True)
            return True
        if ftlog.is_debug():
            ftlog.debug('user_share_behavior.isValidDatetime dateTimeStr=', dateTimeStr, 'ret=', False)
        return False
    except Exception:
        return False


def saveUserBehaviorData(userId, dataStr):
    daobase.executeUserCmd(userId, 'HSET', 'userBehavior:' + str(DIZHU_GAMEID) + ':' + str(userId), 'shareBehavior', dataStr)
    if ftlog.is_debug():
        ftlog.debug('user_share_behavior.saveUserBehaviorData userId=', userId, 'dataStr=', dataStr)


def loadUserBehaviorData(userId):
    dataStr = daobase.executeUserCmd(userId, 'HGET', 'userBehavior:' + str(DIZHU_GAMEID) + ':' + str(userId), 'shareBehavior')
    if ftlog.is_debug():
        ftlog.debug('user_share_behavior.loadUserBehaviorData userId=', userId, 'dataStr=', dataStr)
    return dataStr



class BurialData(object):
    def __init__(self):
        self.burialId = None
        self.watchCount = 0

    def fromDict(self, d):
        self.burialId = d.get('burialId')
        self.watchCount = d.get('watchCount', 0)
        return self

    def toDict(self):
        return {
            'burialId': self.burialId,
            'watchCount': self.watchCount
        }

class UserShareBehaviorData(object):
    def __init__(self, userId):
        self.userId = userId
        self.burialList = []
        self.dateTimeStr = None

    def fromDict(self, d):
        self.dateTimeStr = d.get('dateTimeStr')
        for burialInfo in d.get('burialList', []):
            self.burialList.append(BurialData().fromDict(burialInfo))
        return self

    def toDict(self):
        return {
            'dateTimeStr': self.dateTimeStr,
            'burialList': [burialInfo.toDict() for burialInfo in self.burialList]
        }

    def getBurialLeftCount(self, burialConfInfo):
        for burialInfo in self.burialList:
            if burialInfo.burialId == burialConfInfo.get('burialId'):
                return burialConfInfo.get('dailyCount', 0) - burialInfo.watchCount
        self.burialList.append(BurialData().fromDict(burialConfInfo))
        return burialConfInfo.get('dailyCount', 0)

    def increaseBurialWatchCount(self, burialId):
        for burialInfo in self.burialList:
            if burialInfo.burialId == burialId:
                dailyCount = getBurialConf(burialId).get('dailyCount', 0)
                burialInfo.watchCount = min(dailyCount, burialInfo.watchCount + 1)
                if ftlog.is_debug():
                    ftlog.debug('user_share_behavior.UserShareBehaviorData.increaseBurialWatchCount userId=', self.userId,
                                'burialId=', burialId,
                                'watchCount=', burialInfo.watchCount,
                                'dailyCount=', dailyCount)


def getUserShareBehaviorConf():
    return configure.getGameJson(DIZHU_GAMEID, 'user.share.behavior', {})


def getBurialConf(burialId):
    confList = getUserShareBehaviorConf().get('burialIdList')
    for conf in confList:
        if conf.get('burialId') == burialId:
            return conf
    return {}


def doGetUserShareBehaviorInfo(userId):
    # redis 中获取， 存储在 dizhuaccount.loginGame 中
    share_behavior = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, 'shareBehaviorFeature')
    if ftlog.is_debug():
        ftlog.debug('user_share_behavior.doGetUserShareBehaviorInfo',
                    'userId=', userId,
                    'share_behavior=', share_behavior)
    burial_list = []
    if getUserShareBehaviorConf().get('test_sharing_behavior'):
        share_behavior = getUserShareBehaviorConf().get('test_sharing_behavior')
    if share_behavior:
        # 特征库中字段名share_behavior
        # 格式：
        # YYYY - MM - DD:[0 | 1]: % d: % d
        # 例子：
        # 2018 - 06 - 13:1:5:7
        # 第一个字段表示这是2018年6月13日凌晨4点到2018年6月14日凌晨4点有效的数据
        # 第二个字段位0表示这个用户有过分享，1
        # 表示这个用户没有分享过，例子中为1
        # 第三个字段表示这个用户前7天总共拉来的新增，例子中为5
        # 第四个字段表示这个用户前7天总共唤醒数量，例子中为7
        try:

            timeStr, isShare, _, _ = share_behavior.split(':')
            if not isValidDatetime(timeStr):
                return {}

            if isShare:
                # 加载用户数据
                dataStr = loadUserBehaviorData(userId)
                if dataStr:
                    userData = UserShareBehaviorData(userId).fromDict(json.loads(dataStr))
                    if userData.dateTimeStr != timeStr:
                        userData.dateTimeStr = timeStr
                        userData.burialList = []
                else:
                    userData = UserShareBehaviorData(userId)
                    userData.dateTimeStr = timeStr
                conf = getUserShareBehaviorConf()
                videoOrBanner = conf.get('videoOrBanner', '')
                for burialConfInfo in conf.get('burialIdList', []):
                    leftCount = userData.getBurialLeftCount(burialConfInfo)
                    burial_list.append({
                        'burialId': burialConfInfo.get('burialId'),
                        'dailyCount': burialConfInfo.get('dailyCount'),
                        'leftCount': leftCount
                    })
                if ftlog.is_debug():
                    ftlog.debug('user_share_behavior.doGetUserShareBehaviorInfo result',
                                'userId=', userId,
                                'burial_list=', burial_list,
                                'isShare=', isShare)
                saveUserBehaviorData(userId, json.dumps(userData.toDict()))
                return {
                    'burial_list': burial_list,
                    'isShare': isShare,
                    'videoOrBanner': videoOrBanner
                }
            return {}
        except Exception:
            return {}
    else:
        return {}



def doUserShareBehaviorDealResult(userId, burialId):
    ''' 核心业务处理 '''
    ret = {}
    leftCount = 0
    if burialId == 'segementRecover':
        leftCount = _processRecover(userId, burialId)
    return leftCount, ret

def _processRecover(userId, burialId):
    userRecoverData = SegmentMatchHelper.getUserSegmentRecoverData(userId)
    leftCount = 0
    if userRecoverData.active:
        dataStr = loadUserBehaviorData(userId)
        if dataStr:
            userData = UserShareBehaviorData(userId).fromDict(json.loads(dataStr))
            userData.increaseBurialWatchCount(burialId)
            saveUserBehaviorData(userId, json.dumps(userData.toDict()))
            burialConf = getBurialConf(burialId)
            leftCount = userData.getBurialLeftCount(burialConf)

            userRecoverData.shareRecoverCount += 1
            SegmentMatchHelper.saveUserSegmentRecoverData(userId, userRecoverData)

            # 广播事件
            TGDizhu.getEventBus().publishEvent(SegmentRecoverEvent(userId, DIZHU_GAMEID))
    return leftCount


def getNoInvitedDiamond(userId):
    # redis 中获取， 存储在 dizhuaccount.loginGame 中
    noInvitedGetDiamond = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, 'noInvitedGetDiamond')
    burialId = getUserShareBehaviorConf().get('noInvitedGetDiamondBurialId')
    if ftlog.is_debug():
        ftlog.debug('user_share_behavior.getNoInvitedDiamond',
                    'userId=', userId,
                    'noInvitedGetDiamond=', noInvitedGetDiamond)

    if getUserShareBehaviorConf().get('test_noInvitedGetDiamond'):
        noInvitedGetDiamond = getUserShareBehaviorConf().get('test_noInvitedGetDiamond')
    if noInvitedGetDiamond:
        # 目标用户是7日内带来0新增，通过分享领钻石 > 3，非3天内注册用户。
        # 我们将这部分特征写入了特征库
        # 字段：no_invited_get_diamond
        # 值：有效期:实际领钻石的数量
        # 说明：天还是以凌晨4:00 - 次日凌晨4:00
        # 为一天
        #
        # 示例：
        # 2018-07-18:4
        # 表示2018-07-18 4:00-2018-07-19 4:00该字段有效，该用户在之前7日共通过分享领钻石获得了4个钻石。
        try:
            timeStr, _ = noInvitedGetDiamond.split(':')
            if not isValidDatetime(timeStr):
                return 0, burialId
            return 1, burialId
        except Exception:
            return 0, burialId
    else:
        return 0, burialId


def isInterventionUser(userId):
    # redis 中获取， 存储在 dizhuaccount.loginGame 中
    roundsShareTimes = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, 'roundsShareTimes')
    if ftlog.is_debug():
        ftlog.debug('user_share_behavior.isInterventionUser',
                    'userId=', userId,
                    'roundsShareTimes=', roundsShareTimes)

    if getUserShareBehaviorConf().get('test_roundsShareTimes'):
        roundsShareTimes = getUserShareBehaviorConf().get('test_roundsShareTimes')
    if roundsShareTimes:
        try:
            timeStr, playTimes, shareTimes = roundsShareTimes.split(':')
            if isValidDatetime(timeStr):
                shareRate = float(shareTimes) / float(playTimes)
                if ftlog.is_debug():
                    ftlog.debug('user_share_behavior.isInterventionUser',
                                'userId=', userId,
                                'timeStr=', timeStr,
                                'playTimes=', playTimes,
                                'shareTimes=', shareTimes,
                                'shareRate=', shareRate,
                                'roundsShareTimes=', roundsShareTimes)
                if shareRate < 0.2:
                    return 1
        except Exception, e:
            ftlog.error('user_share_behavior.isInterventionUser error',
                        'userId=', userId,
                        'error=', e.message)
            return 0

    return 0
