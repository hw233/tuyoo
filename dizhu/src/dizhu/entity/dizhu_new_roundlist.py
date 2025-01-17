# -*- coding:utf-8 -*-
import json

import freetime.util.log as ftlog
import poker.entity.events.tyeventbus as pkeventbus
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.games.segmentmatch.events import SegmentTableWinloseEvent
from dizhucomm.entity.events import UserTableWinloseEvent
from poker.entity.configure import configure
from poker.entity.dao import gamedata
from poker.entity.events.tyevent import EventConfigure

_inited = False
_roundListConf = None


def buildUserRoundKey():  # 用户五维图信息
    return 'roundlist'


def buildUserDataTotalKey():  # 用户总信息
    return 'roundlist:total'


def buildUserRoundStateKey():  # 用户五维图解锁状态
    return 'roundlist:state'


def _initialize():
    ftlog.debug('dizhu_new_roundlist._initialize begin')
    global _inited
    if not _inited:
        _inited = True
        _reloadConf()
        pkeventbus.globalEventBus.subscribe(EventConfigure, _onConfChanged)
        subscribeSegmentTableWinlose()
        subscribeNormalTableWinlose()

    ftlog.debug('dizhu_new_roundlist._initialize end')


def _onConfChanged(event):
    if _inited and event.isChanged('game:6:roundlist:0'):
        ftlog.debug('dizhu_new_roundlist._onConfChanged')
        _reloadConf()


def _reloadConf():
    global _roundListConf
    _roundListConf = configure.getGameJson(DIZHU_GAMEID, 'roundlist', {}, 0)

    ftlog.info('dizhu_new_roundlist._reloadConf succeed',
               '_roundListConf=', _roundListConf)


def subscribeSegmentTableWinlose():
    from dizhu.game import TGDizhu
    TGDizhu.getEventBus().subscribe(SegmentTableWinloseEvent, _processNewRoundList)


def subscribeNormalTableWinlose():
    from dizhu.game import TGDizhu
    TGDizhu.getEventBus().subscribe(UserTableWinloseEvent, _processNewRoundList)


class UserRoundInfo(object):
    ''' 局数据-五维图 '''

    def __init__(self):
        self.outCardSeconds = 0
        self.assist = 0
        self.isWin = 0
        self.validMaxOutCard = 0

    def fromDict(self, d):
        self.outCardSeconds = d.get('outCardSeconds', 0)
        self.assist = d.get('assist', 0)
        self.isWin = d.get('isWin', 0)
        self.validMaxOutCard = d.get('validMaxOutCard', 0)
        return self

    def toDict(self):
        return {
            'outCardSeconds': self.outCardSeconds,
            'assist': self.assist,
            'isWin': self.isWin,
            'validMaxOutCard': self.validMaxOutCard
        }


class UserRoundListDataTotal(object):

    def __init__(self):
        self.totalPlayCount = 0
        self.totalWinCount = 0

    def fromDict(self, d):
        self.totalPlayCount = d.get('totalPlayCount', 0)
        self.totalWinCount = d.get('totalWinCount', 0)
        return self

    def toDict(self):
        return {
            'totalPlayCount': self.totalPlayCount,
            'totalWinCount': self.totalWinCount
        }


def saveUserRoundInfo(userId, roundInfo):
    ''' 保存用户局信息, 最多保存30局 '''
    if ftlog.is_debug():
        ftlog.debug('saveUserRoundInfo userId=', userId,
                    'roundInfo=', roundInfo,
                    'roundInfoDict=', roundInfo.toDict())
    roundListCount = _roundListConf.get('roundListCount', 30)
    key = buildUserRoundKey()
    roundInfoList = gamedata.getGameAttr(userId, DIZHU_GAMEID, key)
    if roundInfoList:
        roundInfoList = json.loads(roundInfoList)
    else:
        roundInfoList = []
    roundInfoList.append(roundInfo.toDict())
    gamedata.setGameAttr(userId, DIZHU_GAMEID, key, json.dumps(roundInfoList[-roundListCount:]))


def saveUserRoundDataTotal(userId, data):
    ''' 保存用户五维图总局数等信息 '''
    key = buildUserDataTotalKey()
    if ftlog.is_debug():
        ftlog.debug('saveUserRoundDataTotal userId=', userId,
                    'key=', key,
                    'data=', data,
                    'dataDict=', data.toDict())
    gamedata.setGameAttr(userId, DIZHU_GAMEID, key, json.dumps(data.toDict()))


def saveUserRoundState(userId):
    gamedata.setGameAttr(userId, DIZHU_GAMEID, buildUserRoundStateKey(), 1)


def getUserRoundState(userId):
    return gamedata.getGameAttr(userId, DIZHU_GAMEID, buildUserRoundStateKey())


def handleRoundList(evt):
    # 五维图信息处理
    userRound = UserRoundInfo()
    userRound.assist = evt.winlose.assist
    userRound.validMaxOutCard = evt.winlose.validMaxOutCard
    userRound.outCardSeconds = evt.winlose.outCardSeconds
    userRound.isWin = evt.winlose.isWin
    saveUserRoundInfo(evt.userId, userRound)


def getUserRoundInfo(userId):
    ''' 获取用户五维图 '''

    outCardSeconds = 0
    assist = 0
    winCount = 0
    validMaxOutCard = 0

    roundInfoList = gamedata.getGameAttr(userId, DIZHU_GAMEID, buildUserRoundKey())
    if roundInfoList:
        roundInfoList = json.loads(roundInfoList)
        roundList = [UserRoundInfo().fromDict(d) for d in roundInfoList]
        for roundInfo in roundList:
            outCardSeconds += roundInfo.outCardSeconds
            assist += roundInfo.assist
            winCount += 1 if roundInfo.isWin else 0
            validMaxOutCard += roundInfo.validMaxOutCard

    return {
               'outCardSeconds': outCardSeconds,
               'assist': assist,
               'winCount': winCount,
               'validMaxOutCard': validMaxOutCard
           }, len(roundInfoList if roundInfoList else 0)


def getUserNewRoundInfo(userId):
    ''' 获取用户五维图等信息 '''
    abilityList = None
    roundState = 0
    userTotalInfo = getUserRoundListDataTotal(userId)
    totalPlayCount = userTotalInfo.totalPlayCount
    totalWinCount = userTotalInfo.totalWinCount
    if totalPlayCount == 0:
        winRate = '0'
    else:
        winRate = '%d' % (totalWinCount * 1.0 / totalPlayCount * 100) + '%'
    from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper
    if not SegmentMatchHelper.getUserSegmentDataTotal(userId):
        maxSegment = 1
    else:
        maxSegment = SegmentMatchHelper.getUserSegmentDataTotal(userId).maxSegment
    showRoundCount = _roundListConf.get('showRoundCount', 8)
    if ftlog.is_debug():
        ftlog.debug('getUserNewRoundInfo userId=', userId,
                    'totalPlayCount=', totalPlayCount,
                    'maxSegment=', maxSegment,
                    'showRoundCount=', showRoundCount,
                    'totalWinCount=', totalWinCount)
    if totalPlayCount < showRoundCount:
        return {
            'roundState': roundState,
            'winRate': winRate,
            'totalPlayCount': totalPlayCount,
            'abilityList': abilityList,
            'maxSegment': maxSegment,
            'showRoundCount': showRoundCount
        }

    # if not getUserRoundState(userId):
    #     roundState = 1
    #     return {
    #         'roundState': roundState,
    #         'winRate': winRate,
    #         'totalPlayCount': totalPlayCount,
    #         'abilityList': abilityList,
    #         'maxSegment': maxSegment,
    #         'showRoundCount': showRoundCount
    #     }
    issue = SegmentMatchHelper.getCurrentIssue()
    segment = 1
    userSegmentIssue = SegmentMatchHelper.getUserSegmentDataIssue(userId, issue)
    if userSegmentIssue:
        segment = userSegmentIssue.segment
    if ftlog.is_debug():
        ftlog.debug('getUserNewRoundInfo userId=', userId,
                    'issue=', issue,
                    'segment=', segment)
    # 获取五维图信息
    roundState = 2
    userRoundInfo, length = getUserRoundInfo(userId)
    # 计算局均出牌时间
    outSeconds = round(userRoundInfo['outCardSeconds'] * 1.0 / length, 2)
    if outSeconds >= 60:
        outcardRate = 0
    elif outSeconds <= 15:
        outcardRate = 1
    else:
        outcardRate = 1 - (round((outSeconds - 15) * 1.0 / 45, 2))
    abilityList = [round(userRoundInfo['winCount'] * 1.0 / length, 2),
                   outcardRate,
                   round(userRoundInfo['assist'] * 1.0 / length, 2),
                   round(userRoundInfo['validMaxOutCard'] * 1.0 / length, 2),
                   round(segment * 1.0 / 25, 2)
                   ]
    return {
        'roundState': roundState,
        'winRate': winRate,
        'totalPlayCount': totalPlayCount,
        'abilityList': abilityList,
        'maxSegment': maxSegment,
        'showRoundCount': showRoundCount
    }


def getUserRoundListDataTotal(userId):
    ''' 获取用户天梯赛总信息 '''
    key = buildUserDataTotalKey()
    data = gamedata.getGameAttr(userId, DIZHU_GAMEID, key)
    if ftlog.is_debug():
        ftlog.debug('getUserRoundListDataTotal userId=', userId,
                    'data=', data)
    if data:
        data = json.loads(data)
        if ftlog.is_debug():
            ftlog.debug('getUserRoundListDataTotal userId=', userId,
                        'haveDateIns')
        return UserRoundListDataTotal().fromDict(data)
    if ftlog.is_debug():
        ftlog.debug('getUserRoundListDataTotal userId=', userId,
                    'newRoundIns')
    return UserRoundListDataTotal()


def _processNewRoundList(evt):
    if not _roundListConf.get('switch', 0):
        return
    handleRoundList(evt)
    userRoundTotal = getUserRoundListDataTotal(evt.userId)
    if ftlog.is_debug():
        ftlog.debug('_processNewRoundList before userId=', evt.userId,
                    'totalPlayCount=', userRoundTotal.totalPlayCount,
                    'totalWinCount=', userRoundTotal.totalWinCount)
    userRoundTotal.totalPlayCount += 1
    userRoundTotal.totalWinCount += 1 if evt.winlose.isWin else 0
    if ftlog.is_debug():
        ftlog.debug('_processNewRoundList after userId=', evt.userId,
                    'totalPlayCount=', userRoundTotal.totalPlayCount,
                    'totalWinCount=', userRoundTotal.totalWinCount)
    saveUserRoundDataTotal(evt.userId, userRoundTotal)



