# -*- coding:utf-8 -*-
'''
Created on 2018-04-15

@author: wangyonghui
'''
import json
import datetime

from dizhu.entity import dizhuconf
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.led_util import LedUtil
from dizhu.entity.official_counts.events import OfficialMessageEvent
from dizhu.entity.segment.dao import segmentdata
from dizhu.entity.wx_share_control import WxShareControlHelper
from hall.entity import hall_share3
from hall.entity.hallconf import HALL_GAMEID
from hall.entity.usercoupon import user_coupon_details
from hall.entity.usercoupon.events import UserCouponReceiveEvent
from dizhu.games.segmentmatch.events import SegmentTableWinloseEvent, SegmentRecoverEvent
from freetime.entity.msg import MsgPack
from hall.entity.hallevent import HallShare3Event, HallWithdrawCashEvent
from hall.entity.hallusercond import UserConditionRegister
from poker.entity.biz import bireport
from poker.entity.biz.content import TYContentItem
from poker.entity.biz.exceptions import TYBizConfException
from poker.entity.configure import configure
from poker.entity.events.tyevent import EventConfigure, EventHeartBeat
import poker.entity.events.tyeventbus as pkeventbus
from poker.entity.dao import daobase, sessiondata, userdata
import poker.entity.dao.userdata as pkuserdata
from poker.protocol import router
from poker.util import timestamp as pktimestamp
import freetime.util.log as ftlog
from sre_compile import isstring


# 数据库Key管理, Reply 库
def buildRankListKey(issue):   # 排行榜
    return 'segment.rankList:%s:%s' % (DIZHU_GAMEID, issue)


def buildRewardsPoolKey(issue):  # 进入最终奖池的用户(set类型)
    return 'segment.rewardsPool:%s:%s' % (DIZHU_GAMEID, issue)


def buildIssueStateKey():
    return 'segment.issueStateList:%s' % DIZHU_GAMEID


def buildUserSegmentRoundKey():   # 用户五维图信息
    return 'segmentMatch:roundlist'


def buildUserSegmentMatchKey():  # 用户总信息
    return 'segmentMatch'


def buildUserSegmentIssues():   # 用户参加过得赛季
    return 'segmentIssueList'


def buildUserSegmentIssueInfo(issue):   # 用户当前赛季信息
    return 'segmentMatch:%s' % issue


def buildUserSegmentRecoverKey():   # 段位恢复
    return 'segmentRecover'

def buildUserSegmentTableWinRewardKey():   # 牌桌奖励， count, timestamp
    return 'tableWinReward'

def buildUserSegmentWinStreakTaskKey():  # 连胜任务
    return 'winStreakTask'


class SegmentInfoConf(object):
    '''
    段位信息，包括段位，段位星数，调星保护，报名费，段位名称
    '''
    def __init__(self):
        self.segment = None
        self.stars = None
        self.inherit = None
        self.starProtection = None
        self.segmentProtection = None
        self.title = None

    def decodeFromDict(self, d):
        self.segment = d.get('segment')
        if not isinstance(self.segment, int):
            raise TYBizConfException(d, 'SegmentSingleConf.segment must be int')

        self.stars = d.get('stars')
        if not isinstance(self.stars, int):
            raise TYBizConfException(d, 'SegmentSingleConf.stars must be int')

        self.inherit = d.get('inherit', 0)
        if not isinstance(self.inherit, int):
            raise TYBizConfException(d, 'SegmentSingleConf.inherit must be int')

        self.starProtection = d.get('starProtection')
        if not isinstance(self.starProtection, int) and self.starProtection not in (0, 1):
            raise TYBizConfException(d, 'SegmentSingleConf.starProtection must be int and in [0, 1]')

        self.segmentProtection = d.get('segmentProtection')
        if not isinstance(self.segmentProtection, int) and self.segmentProtection not in (0, 1):
            raise TYBizConfException(d, 'SegmentSingleConf.segmentProtection must be int and in [0, 1]')

        self.title = d.get('title')
        if not isstring(self.title):
            raise TYBizConfException(d, 'SegmentSingleConf.title must be str')
        return self


class SeasonInfoConf(object):
    '''
    赛季信息，包括开始结束时间，赛季号，奖池相关信息
    '''
    def __init__(self):
        self.startTime = None
        self.endTime = None
        self.issueNum = None
        self.seasonNum = None
        self.poolRewards = None
        self.seasonTips = None
        self.mainPicture = None
        self.mainPicture2 = None

    def decodeFromDict(self, d):
        startTime = d.get('startTime')
        try:
            startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            self.startTime = startTime
        except Exception:
            raise TYBizConfException(d, 'SegmentSingleConf.startTime must be like "2018-05-14 00:00:00"')

        endTime = d.get('endTime')
        try:
            endTime = datetime.datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")
            self.endTime = endTime
        except Exception:
            raise TYBizConfException(d, 'SegmentSingleConf.endTime must be like "2018-05-14 00:00:00"')

        self.issueNum = d.get('issueNum')
        if not isstring(self.issueNum):
            raise TYBizConfException(d, 'SegmentSingleConf.issueNum must str')

        self.seasonNum = d.get('seasonNum')
        if not isinstance(self.seasonNum, int):
            raise TYBizConfException(d, 'SegmentSingleConf.seasonNum must be int')

        self.poolRewards = d.get('poolRewards', {})
        if not isinstance(self.poolRewards, dict):
            raise TYBizConfException(d, 'SegmentSingleConf.poolRewards must be dict')

        self.seasonTips = d.get('seasonTips', [])
        if not isinstance(self.seasonTips, list):
            raise TYBizConfException(d, 'SegmentSingleConf.seasonTips must be dict')

        self.mainPicture = d.get('mainPicture', {})
        if not isinstance(self.mainPicture, dict):
            raise TYBizConfException(d, 'SegmentSingleConf.mainPicture must be dict')

        self.mainPicture2 = d.get('mainPicture2', {})
        if not isinstance(self.mainPicture2, dict):
            raise TYBizConfException(d, 'SegmentSingleConf.mainPicture2 must be dict')
        return self


class SegmentMatchConf(object):
    '''
    段位赛总配置
    '''
    def __init__(self):
        self.closed = None
        self.saveRecordCount = None
        self.roundListCount = None
        self.seasonTips = None
        self.segmentTips = None
        self.mail = None
        self.segments = None
        self.seasonRewards = None
        self.rankCacheTime = None
        self.rankRecordCount = None
        self.seasonList = None
        self.segmentRecover = None
        self.gameWinReward = None
        self.mainPicture = None
        self.tableWinStreakTask = None
        self.addUserStar = None

    def decodeFromDict(self, d):
        self.closed = d.get('closed')
        if not isinstance(self.closed, int) or self.closed not in (0, 1):
            raise TYBizConfException(d, 'SegmentConf.closed must be int and in [0, 1]')

        self.saveRecordCount = d.get('saveRecordCount')
        if not isinstance(self.saveRecordCount, int):
            raise TYBizConfException(d, 'SegmentConf.saveRecordCount must be int')

        self.roundListCount = d.get('roundListCount')
        if not isinstance(self.roundListCount, int):
            raise TYBizConfException(d, 'SegmentConf.roundListCount must be int')

        self.seasonTips = d.get('seasonTips', [])
        if not isinstance(self.seasonTips, list):
            raise TYBizConfException(d, 'SegmentConf.seasonTips must be list')

        self.segmentTips = d.get('segmentTips')
        if not isinstance(self.segmentTips, list):
            raise TYBizConfException(d, 'SegmentConf.segmentTips must be list')

        self.mail = d.get('mail')
        if not isstring(self.mail):
            raise TYBizConfException(d, 'SegmentConf.mail must be str')

        seasonList = d.get('seasonList')
        if not isinstance(seasonList, list):
            raise TYBizConfException(d, 'SegmentConf.seasonList must be list')
        self.seasonList = []
        for seasonConf in seasonList:
            seasonInfo = SeasonInfoConf().decodeFromDict(seasonConf)
            self.seasonList.append(seasonInfo)

        seasonRewards = d.get('seasonRewards')
        if not isinstance(seasonRewards, list):
            raise TYBizConfException(d, 'SegmentConf.seasonRewards must be list')
        self.seasonRewards = []
        for seasonConf in seasonRewards:
            for key in seasonConf.keys():
                if key not in ['segments', 'rewards', 'title', 'rewardShow']:
                    raise TYBizConfException(d, 'SegmentConf.seasonRewards conf error')
            try:
                TYContentItem.decodeList(seasonConf['rewards'])
            except Exception:
                raise TYBizConfException(d, 'SegmentConf.seasonRewards conf error')
            self.seasonRewards.append(seasonConf)

        self.rankCacheTime = d.get('rankCacheTime')
        if not isinstance(self.rankCacheTime, int) or self.rankCacheTime <= 0:
            raise TYBizConfException(d, 'SegmentConf.rankCacheTime must be int')

        self.rankRecordCount = d.get('rankRecordCount')
        if not isinstance(self.rankRecordCount, int) or self.rankRecordCount <= 0:
            raise TYBizConfException(d, 'SegmentConf.rankRecordCount must be int')

        segments = d.get('segments')
        if not isinstance(segments, list):
            raise TYBizConfException(d, 'SegmentConf.segments must be list')
        self.segments = []
        for segConf in segments:
            singleConf = SegmentInfoConf().decodeFromDict(segConf)
            self.segments.append(singleConf)

        self.segmentRecover = d.get('segmentRecover')
        if not isinstance(self.segmentRecover, dict):
            raise TYBizConfException(d, 'SegmentConf.segmentRecover must be dict')

        self.gameWinReward = d.get('gameWinReward')
        if not isinstance(self.gameWinReward, dict):
            raise TYBizConfException(d, 'SegmentConf.gameWinReward must be dict')

        self.mainPicture = d.get('mainPicture', {})
        if not isinstance(self.mainPicture, dict):
            raise TYBizConfException(d, 'SegmentConf.mainPicture must be dict')

        self.tableWinStreakTask = d.get('tableWinStreakTask', [])
        if not isinstance(self.tableWinStreakTask, list):
            raise TYBizConfException(d, 'SegmentConf.tableWinStreakTask must be dict')

        self.addUserStar = d.get('addUserStar', {})
        if not isinstance(self.addUserStar, dict):
            raise TYBizConfException(d, 'SegmentConf.addUserStar must be dict')

        return self

    def getSegmentInfo(self, segment):
        segment = segment or 1
        for segConf in self.segments:
            if segConf.segment == int(segment):
                return segConf
        return None

    def getSeasonRewards(self, segment):
        segment = int(segment)
        for seasonReward in self.seasonRewards:
            if segment in seasonReward['segments']:
                return seasonReward['rewards']
        return None

    def getSeasonTips(self):
        ret = self.seasonTips
        seasonInfo = SegmentMatchHelper.getSeasonInfo()
        if seasonInfo and seasonInfo.seasonTips:
            ret = seasonInfo.seasonTips
        return ret

    def getMainPicture(self):
        ret = self.mainPicture
        seasonInfo = SegmentMatchHelper.getSeasonInfo()
        if seasonInfo and seasonInfo.mainPicture:
            ret = seasonInfo.mainPicture
        return ret

    def getMainPicture2(self):
        ret = self.mainPicture
        seasonInfo = SegmentMatchHelper.getSeasonInfo()
        if seasonInfo and seasonInfo.mainPicture2:
            ret = seasonInfo.mainPicture2
        return ret

class UserSegmentRoundInfo(object):
    ''' 局数据-五维图 '''
    def __init__(self):
        self.outCardSeconds = 0      # 出牌时间（速度）
        self.bombs = 0               # 炸弹（ 刚烈）
        self.isWin = 0               # 是否胜利 （常胜）
        self.isDizhu = 0             # 是否地主 (独立)
        self.leadWin = 0             # 当农民且出完手牌（带飞）

    def fromDict(self, d):
        self.outCardSeconds = d.get('outCardSeconds', 0)
        self.bombs = d.get('bombs', 0)
        self.isWin = d.get('isWin', 0)
        self.isDizhu = d.get('isDizhu', 0)
        self.leadWin = d.get('leadWin', 0)
        return self

    def toDict(self):
        return {
            'outCardSeconds': self.outCardSeconds,
            'bombs': self.bombs,
            'isWin': self.isWin,
            'isDizhu': self.isDizhu,
            'leadWin': self.leadWin
        }


class UserSegmentDataIssue(object):
    ''' 用户当前赛季数据 '''
    IDEAL = 0                   # 未处理
    HAS_NO_REWARD = 1           # 未得奖
    HAS_RECEIVED = 2            # 已领取状态

    def __init__(self):
        self.rank = 0                            # 结算时名次
        self.segment = 1                         # 段位
        self.inherit = 0                         # 当前段位继承
        self.currentStar = 0                     # 当前段位星数
        self.poolRewardsState = self.IDEAL       # 领奖状态
        self.segmentRewardsState = self.IDEAL    # 用户奖励

    def fromDict(self, d):
        self.rank = d.get('rank')
        self.segment = d.get('segment', 0)
        self.inherit = d.get('inherit', 0)
        self.currentStar = d.get('currentStar', 0)
        self.poolRewardsState = d.get('poolRewardsState', 0)
        self.segmentRewardsState = d.get('segmentRewardsState', 0)
        return self

    def toDict(self):
        return {
            'rank': self.rank,
            'segment': self.segment,
            'inherit': self.inherit,
            'currentStar': self.currentStar,
            'poolRewardsState': self.poolRewardsState,
            'segmentRewardsState': self.segmentRewardsState
        }


class UserSegmentDataTotal(object):
    ''' 用户段位赛总数据 '''

    def __init__(self):
        self.winStreak = 0                  # 连胜
        self.maxWinStreak = 0               # 最高连胜
        self.maxSegment = 0                 # 历史最高段位
        self.totalPlayCount = 0             # 玩得总局数
        self.totalWinCount = 0              # 胜利局数
        self.leadWinCount = 0               # 农民且最后一手胜利
        self.dizhuPlayCount = 0             # 当地主次数
        self.winDoubles = 0                 # 最高倍
        self.bombs = 0                      # 扔出炸弹数
        self.outCardSeconds = 0             # 总出牌时间
        self.legendCount = 0                # 徽章次数

    def fromDict(self, d):
        self.winStreak = d.get('winStreak', 0)
        self.maxWinStreak = d.get('maxWinStreak', 0)
        self.maxSegment = d.get('maxSegment', 0)
        self.totalPlayCount = d.get('totalPlayCount', 0)
        self.totalWinCount = d.get('totalWinCount', 0)
        self.leadWinCount = d.get('leadWinCount', 0)
        self.dizhuPlayCount = d.get('dizhuPlayCount', 0)
        self.winDoubles = d.get('winDoubles', [])
        self.bombs = d.get('bombs', 0)
        self.outCardSeconds = d.get('outCardSeconds', 0)
        self.legendCount = d.get('legendCount', 0)
        return self

    def toDict(self):
        return {
            'winStreak': self.winStreak,
            'maxWinStreak': self.maxWinStreak,
            'maxSegment': self.maxSegment,
            'totalPlayCount': self.totalPlayCount,
            'totalWinCount': self.totalWinCount,
            'leadWinCount': self.leadWinCount,
            'dizhuPlayCount': self.dizhuPlayCount,
            'winDoubles': self.winDoubles,
            'bombs': self.bombs,
            'outCardSeconds': self.outCardSeconds,
            'legendCount': self.legendCount
        }


class UserSegmentRecoverData(object):
    ''' 用户段位保护数据 '''

    def __init__(self):
        self.active = 0             # 是否激活
        self.shareRecoverCount = 0  # 分享复活次数
        self.totalRecoverCount = 0  # 总复活次数
        self.timestamp = 0          # 时间戳，每天清零

    def fromDict(self, d):
        self.active = d.get('active', 0)
        self.shareRecoverCount = d.get('shareRecoverCount', 0)
        self.totalRecoverCount = d.get('totalRecoverCount', 0)
        self.timestamp = d.get('timestamp', 0)
        return self

    def toDict(self):
        return {
            'active': self.active,
            'shareRecoverCount': self.shareRecoverCount,
            'totalRecoverCount': self.totalRecoverCount,
            'timestamp': self.timestamp
        }


_inited = False
_issueList = []
_segmentConf = None

def getSegmentConf():
    return _segmentConf


def _reloadConf():
    global _segmentConf
    d = configure.getGameJson(DIZHU_GAMEID, 'match.segment', {}, 0)
    conf = SegmentMatchConf().decodeFromDict(d)
    _segmentConf = conf

    ftlog.info('dizhu_segment_match._reloadConf succeed',
               '_segmentConf=', _segmentConf)

def _onConfChanged(event):
    if _inited and event.isChanged('game:6:match.segment:0'):
        ftlog.debug('dizhu_segment_match._onConfChanged')
        _reloadConf()


def subscribeTableWinlose():
    from dizhu.game import TGDizhu
    TGDizhu.getEventBus().subscribe(SegmentTableWinloseEvent, _processUserWinloseSegment)


def subscribeSegmentRecover():
    from dizhu.game import TGDizhu
    TGDizhu.getEventBus().subscribe(SegmentRecoverEvent, _processUserSegmentRecover)

def subscribeHallShare3():
    from hall.game import TGHall
    TGHall.getEventBus().subscribe(HallShare3Event, _processUserShare)

def subscribeHallWithdrawCashEvent():
    from hall.game import TGHall
    TGHall.getEventBus().subscribe(HallWithdrawCashEvent, _processUserCash)


def _initialize(isCenter):
    ftlog.debug('dizhu_segment_match._initialize begin')
    global _inited
    if not _inited:
        _inited = True
        _reloadConf()
        pkeventbus.globalEventBus.subscribe(EventConfigure, _onConfChanged)
        subscribeTableWinlose()
        subscribeSegmentRecover()
        subscribeHallShare3()
        subscribeHallWithdrawCashEvent()
        if isCenter:
            from poker.entity.events.tyeventbus import globalEventBus
            globalEventBus.subscribe(EventHeartBeat, _onTimer)

    ftlog.debug('dizhu_segment_match._initialize end')


_processRankingInterval = 300   # 每5分钟处理一次排行榜
_prevProcessRankingTimestamp = 0

def _onTimer(evt):
    global _prevProcessRankingTimestamp
    timestamp = pktimestamp.getCurrentTimestamp()
    if not _prevProcessRankingTimestamp or timestamp - _prevProcessRankingTimestamp > _processRankingInterval:
        _prevProcessRankingTimestamp = timestamp
        _processIssueStateList()

def _processIssueStateList(forceSettle=0):
    ''' 处理赛季是否结束 '''
    issues = SegmentMatchHelper.getIssueStateList()

    for issuestate in issues:
        seasonInfo = SegmentMatchHelper.getSeasonInfo(issuestate['issue'])
        if ftlog.is_debug():
            ftlog.debug('dizhu_segment_match._processIssueStateList issuestate=', issuestate,
                        'seasonInfo=', seasonInfo)
        if not seasonInfo:
            continue
        endTime = seasonInfo.endTime
        now = datetime.datetime.now()
        if now > endTime or forceSettle:
            # 处理赛季奖池
            seasonInfo = SegmentMatchHelper.getSeasonInfo(issuestate['issue'])
            if seasonInfo.poolRewards.get('type') == 'rankList':
                _addUserToRewardPool(seasonInfo)
            SegmentMatchHelper.updateIssueState(issuestate['issue'], 1)


def _addUserToRewardPool(seasonInfo, userId=None):
    ''' 添加用户到奖池 '''
    condD = seasonInfo.poolRewards.get('condition')
    key = buildRewardsPoolKey(seasonInfo.issueNum)
    if condD:
        cond = UserConditionRegister.decodeFromDict(condD)
        if seasonInfo.poolRewards.get('type') == 'segment':
            if userId:
                try:
                    userSegmentDataIssue = SegmentMatchHelper.getUserSegmentDataIssue(userId, seasonInfo.issueNum) or UserSegmentDataIssue()
                    clientId = sessiondata.getClientId(userId)
                    ret = cond.check(DIZHU_GAMEID, userId, clientId, pktimestamp.getCurrentTimestamp(), segment=userSegmentDataIssue.segment, rank=userSegmentDataIssue.rank)
                    if ret:
                        daobase.executeRePlayCmd('sadd', key, userId)
                        if ftlog.is_debug():
                            ftlog.debug('_addUserToRewardPool userId=', userId, 'type=', seasonInfo.poolRewards.get('type'),
                                        'issue=', seasonInfo.issueNum,
                                        'totalUserList=', daobase.executeRePlayCmd('SMEMBERS', key))
                except Exception, e:
                    ftlog.error('_addUserToRewardPool error userId=', userId, 'type=', seasonInfo.poolRewards.get('type'), 'issue=', seasonInfo.issueNum, 'errmsg=', e.message)
        else:
            userIdList = getRanklist(seasonInfo.issueNum, 0, -1)
            for rank, userId in enumerate(userIdList, 1):
                try:
                    userSegmentDataIssue = SegmentMatchHelper.getUserSegmentDataIssue(userId, seasonInfo.issueNum) or UserSegmentDataIssue()
                    clientId = sessiondata.getClientId(userId)
                    ret = cond.check(DIZHU_GAMEID, userId, clientId, pktimestamp.getCurrentTimestamp(), segment=userSegmentDataIssue.segment, rank=rank)
                    if ret:
                        daobase.executeRePlayCmd('sadd', key, userId)
                        if ftlog.is_debug():
                            ftlog.debug('_addUserToRewardPool userId=', userId, 'type=', seasonInfo.poolRewards.get('type'),
                                        'issue=', seasonInfo.issueNum,
                                        'totalUserList=', daobase.executeRePlayCmd('SMEMBERS', key))
                except Exception, e:
                    ftlog.error('_addUserToRewardPool error userId=', userId, 'type=', seasonInfo.poolRewards.get('type'), 'issue=', seasonInfo.issueNum, 'errmsg=', e.message)



# --------------------------------------------------
# 排行榜相关函数（运行于CT）
# --------------------------------------------------

def insertRanklist(issue, userId, totalStar, rankLimit=500):
    ''' 插入排行榜 '''
    # score 为 段位 * 100 + star
    assert (rankLimit > 0)
    try:
        key = buildRankListKey(issue)
        daobase.executeRePlayCmd('zadd', key, totalStar, userId)
        removed = daobase.executeRePlayCmd('zremrangebyrank', str(key), 0, -rankLimit - 1)
        if ftlog.is_debug():
            ftlog.debug('dizhu_segment_match.insertRanklist',
                        'userId=', userId,
                        'issue=', issue,
                        'totalStar=', totalStar,
                        'rankLimit=', rankLimit,
                        'removed=', removed)
    except Exception, e:
        ftlog.error('dizhu_segment_match.insertRanklist',
                    'userId=', userId,
                    'issue=', issue,
                    'totalStar=', totalStar,
                    'rankLimit=', rankLimit,
                    'err=', e.message)


def getRanklist(issue, start, stop):
    '''获取排行榜前N名的用户信息'''
    key = buildRankListKey(issue)
    return daobase.executeRePlayCmd('zrevrange', key, start, stop)


def settlementRanking(userId, issue):
    ''' 结算每一期 '''
    global _segmentConf

    userData = SegmentMatchHelper.getUserSegmentDataIssue(userId, issue) or UserSegmentDataIssue()

    # 计算排名（只统计前500名）
    rank = -1
    userIds = getRanklist(issue, 0, -1)
    for index, uId in enumerate(userIds, 1):
        if uId == userId:
            rank = index
    userData.rank = rank
    seasonInfo = SegmentMatchHelper.getSeasonInfo(issue)
    if not seasonInfo:
        return
    startTime = str(seasonInfo.startTime.month) + '月' + str(int(seasonInfo.startTime.day)) + '日'
    endTime = str(seasonInfo.endTime.month) + '月' + str(int(seasonInfo.endTime.day)) + '日'
    # 获取奖励
    rewards = _segmentConf.getSeasonRewards(userData.segment)
    assetList = []
    if userData.segmentRewardsState == UserSegmentDataIssue.IDEAL and rewards:
        contentItems = TYContentItem.decodeList(rewards)
        from dizhu.entity import dizhu_util
        assetList = dizhu_util.sendRewardItems(userId, contentItems, _segmentConf.mail, 'DIZHU_SEGMENT_MATCH_REWARD', int(issue),
                                               startTime=startTime, endTime=endTime, segment=_segmentConf.getSegmentInfo(userData.segment or 1).title)
        userData.segmentRewardsState = UserSegmentDataIssue.HAS_RECEIVED
        ftlog.info('dizhu_segment_match.settlementRanking',
                   'userId=', userId,
                   'issue=', issue,
                   'rank=', rank,
                   'segmentRewards=', rewards)
        try:
            bireport.reportGameEvent('DIZHU_SEGMENT_MATCH_REWARD',
                                     userId,
                                     DIZHU_GAMEID,
                                     0,
                                     0,
                                     0,
                                     0, 0, 0, [int(issue), userData.segment or 1],
                                     sessiondata.getClientId(userId),
                                     0, 0)
        except Exception as e:
            ftlog.info('dizhu_segment_match.settlementRanking',
                       'userId=', userId,
                       'issue=', issue,
                       'rank=', rank,
                       'segmentRewards=', rewards,
                       'err=', e.message)
    else:
        if userData.poolRewardsState == UserSegmentDataIssue.IDEAL:
            userData.segmentRewardsState = UserSegmentDataIssue.HAS_NO_REWARD

    # 发放奖池奖励
    assetPoolList = []
    rewardsPool = seasonInfo.poolRewards.get('rewards')
    rewardPoolKey = buildRewardsPoolKey(issue)
    totalUsers = daobase.executeRePlayCmd('SMEMBERS', rewardPoolKey) or []
    if userData.poolRewardsState == UserSegmentDataIssue.IDEAL and rewardsPool and userId in totalUsers:
        rewardPool = rewardsPool[0]
        everyUserRewards = max(int(rewardPool['count'] / len(totalUsers)), 1)
        from dizhu.entity import dizhu_util
        contentItems = TYContentItem.decodeList([{'itemId': rewardPool['itemId'], 'count': everyUserRewards}])
        assetPoolList = dizhu_util.sendRewardItems(userId, contentItems, seasonInfo.poolRewards.get('mail'), 'DIZHU_SEGMENT_MATCH_POOL_REWARD', int(issue))
        ftlog.info('dizhu_segment_match.settlementRanking pool',
                   'userId=', userId,
                   'issue=', issue,
                   'rank=', rank,
                   'rewardPool=', rewardPool)
        userData.poolRewardsState = UserSegmentDataIssue.HAS_RECEIVED

        try:
            bireport.reportGameEvent('DIZHU_SEGMENT_MATCH_POOL_REWARD',
                                     userId,
                                     DIZHU_GAMEID,
                                     0,
                                     0,
                                     0,
                                     0, 0, 0, [int(issue), userData.segment or 1],
                                     sessiondata.getClientId(userId),
                                     0, 0)
        except Exception as e:
            ftlog.warn('dizhu_segment_match.settlementRanking pool',
                       'userId=', userId,
                       'issue=', issue,
                       'rank=', rank,
                       'rewardPool=', rewardPool,
                       'contentItems=', contentItems,
                       'err=', e.message)


        # 如果是红包券则广播红包券事件
        if rewardPool['itemId'] == 'user:coupon':
            from hall.game import TGHall
            TGHall.getEventBus().publishEvent(
                UserCouponReceiveEvent(HALL_GAMEID, userId, everyUserRewards, user_coupon_details.USER_COUPON_SOURCE_SEGMENT_REWARDS_POOL))
    else:
        if userData.poolRewardsState == UserSegmentDataIssue.IDEAL:
            userData.poolRewardsState = UserSegmentDataIssue.HAS_NO_REWARD
    SegmentMatchHelper.saveUserSegmentDataIssue(userId, issue, userData)
    return assetList, assetPoolList


def _processUserWinloseSegment(evt):
    _handleWinloseSegment(evt)


def _handleWinloseSegment(evt):
    '''
    核心业务之---牌局结束处理用户段位信息（运行于UT）
    '''
    global _issueList
    global _segmentConf
    from hall.game import TGHall
    if _segmentConf.closed or evt.userId < 10000:
        return

    # 添加赛季到赛季列表
    issue = SegmentMatchHelper.getCurrentIssue()
    if not issue:
        ftlog.warn('dizhu_segment_match._handleWinloseSegment',
                   'userId=', evt.userId,
                   'issue=', issue)
        return

    if issue not in _issueList:
        SegmentMatchHelper.saveIssueToIssueStateList(issue)
        _issueList.append(issue)

    # 记录与清理用户过期数据
    SegmentMatchHelper.processUserSegmentIssues(evt.userId, issue)

    # 当前赛季用户信息处理
    currentUserData = SegmentMatchHelper.getUserSegmentDataIssue(evt.userId, issue)
    if not currentUserData:
        currentUserData = UserSegmentDataIssue()
        issueStateList = SegmentMatchHelper.getIssueStateList()
        currentUserData.segment = 1
        if evt.userId >= 10000:
            if issueStateList:
                userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(evt.userId, issueStateList[-1]['issue'])
                if not userSegmentIssueHistory and len(issueStateList) > 1:
                    userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(evt.userId, issueStateList[-2]['issue'])

                if userSegmentIssueHistory and userSegmentIssueHistory.inherit:
                    currentUserData.segment = userSegmentIssueHistory.inherit

    segmentConf = _segmentConf.getSegmentInfo(currentUserData.segment)

    isLevelUp = False

    # 段位复活数据
    userRecoverData = SegmentMatchHelper.getUserSegmentRecoverData(evt.userId)
    userRecoverData.active = 0
    currentTimestamp = pktimestamp.getCurrentTimestamp()
    if not pktimestamp.is_same_day(currentTimestamp, userRecoverData.timestamp):
        userRecoverData.shareRecoverCount = 0
        userRecoverData.totalRecoverCount = 0
        userRecoverData.timestamp = pktimestamp.getCurrentTimestamp()

    if evt.winlose.isWin:
        # punishState=1表示托管获胜，不加星
        if evt.winlose.punishState != 1:
            # 加一颗星, 判断是否达到升段
            stars = segmentConf.stars
            if currentUserData.currentStar < stars:
                currentUserData.currentStar += 1
            else:
                if currentUserData.segment == len(_segmentConf.segments):
                    currentUserData.currentStar += 1
                else:
                    currentUserData.currentStar = 1
                    currentUserData.segment += 1
                    isLevelUp = True
                    # 处理升段微信公众号消息
                    rankInfo = evt.kwargs.get('rankInfo', {})
                    if rankInfo:
                        TGHall.getEventBus().publishEvent(
                            OfficialMessageEvent(DIZHU_GAMEID, evt.userId, dizhuconf.PROMOTE, rankInfo=rankInfo))

                    # 处理达到最高段公众号消息
                    if currentUserData.segment == 25:
                        TGHall.getEventBus().publishEvent(OfficialMessageEvent(DIZHU_GAMEID, evt.userId, dizhuconf.HIGHEST))
    else:
        # punishState=2表示被包赔，不减星
        if evt.winlose.punishState != 2:
            # 减一颗星
            if segmentConf.starProtection != 1:

                if currentUserData.currentStar >= 1:
                    userRecoverData.active = 1

                if currentUserData.currentStar <= 1:
                    if segmentConf.segmentProtection == 1:  # 掉段保护
                        currentUserData.currentStar = max(0, currentUserData.currentStar - 1)
                    else:
                        currentUserData.segment -= 1
                        currentUserData.currentStar = _segmentConf.getSegmentInfo(currentUserData.segment).stars
                        # 更新掉段恢复状态, 后续处理后需要恢复为0
                        userRecoverData.active = 1
                else:
                    currentUserData.currentStar = max(1, currentUserData.currentStar - 1)

    SegmentMatchHelper.saveUserSegmentRecoverData(evt.userId, userRecoverData)

    # 插入排行榜
    insertRanklist(issue, evt.userId, currentUserData.segment * 100 + currentUserData.currentStar, _segmentConf.rankRecordCount)
    # 获取排名
    rank = SegmentMatchHelper.getUserRealRank(evt.userId, issue)
    currentUserData.rank = rank
    # 段位继承
    currentUserData.inherit = _segmentConf.getSegmentInfo(currentUserData.segment).inherit
    # 保存用户信息
    SegmentMatchHelper.saveUserSegmentDataIssue(evt.userId, issue, currentUserData)

    # 五维图信息处理
    userData5 = UserSegmentRoundInfo()
    userData5.bombs = evt.winlose.nBomb
    userData5.leadWin = evt.winlose.leadWin
    userData5.outCardSeconds = evt.winlose.outCardSeconds
    userData5.isDizhu = evt.winlose.isDizhu
    userData5.isWin = evt.winlose.isWin
    SegmentMatchHelper.saveUserSegmentRoundInfo(evt.userId, userData5)

    # 总用户信息处理
    userDataTotal = SegmentMatchHelper.getUserSegmentDataTotal(evt.userId)
    if not userDataTotal:
        userDataTotal = UserSegmentDataTotal()
    userDataTotal.outCardSeconds += evt.winlose.outCardSeconds
    userDataTotal.bombs += evt.winlose.nBomb
    if evt.winlose.isWin:
        userDataTotal.winStreak += 1
    else:
        userDataTotal.winStreak = 0
    userDataTotal.maxWinStreak = max(userDataTotal.winStreak, userDataTotal.maxWinStreak)
    userDataTotal.dizhuPlayCount += 1 if evt.winlose.isDizhu else 0
    userDataTotal.maxSegment = max(userDataTotal.maxSegment, currentUserData.segment)
    userDataTotal.leadWinCount += 1 if evt.winlose.leadWin else 0

    # 印记
    userDataTotal.legendCount += 1 if isLevelUp and currentUserData.segment == len(_segmentConf.segments) else 0

    userDataTotal.totalPlayCount += 1
    userDataTotal.totalWinCount += 1 if evt.winlose.isWin else 0
    userDataTotal.winDoubles = max(userDataTotal.winDoubles, evt.winlose.windoubles)
    SegmentMatchHelper.saveUserSegmentDataTotal(evt.userId, userDataTotal)

    # 瓜分奖池
    seasonInfo = SegmentMatchHelper.getSeasonInfo(issue)
    if seasonInfo.poolRewards.get('type') == 'segment':
        _addUserToRewardPool(seasonInfo, evt.userId)


def _processUserShare(evt):
    ''' 处理段位恢复 '''
    _handleRecover(evt, 'share')
    _handleAddUserStar(evt)


def _processUserSegmentRecover(evt):
    ''' 处理段位恢复 '''
    _handleRecover(evt, 'buy')


def _processUserCash(evt):
    _handleUserCash(evt)


def _handleUserCash(evt):
    nickname, purl = userdata.getAttrs(evt.userId, ['name', 'purl'])
    ledtext = [
        ['FFFFFF', purl],
        ['FFFFFF', nickname],
        ['EC3A24', '%.2f元' % (evt.count/100.0)]
    ]
    LedUtil.sendLed(ledtext, 'global', active=1)
    from hall.game import TGHall
    TGHall.getEventBus().publishEvent(OfficialMessageEvent(HALL_GAMEID, evt.userId, dizhuconf.WITHDRAW, msgParams={'amount': evt.count/100.0}))


def _handleAddUserStar(evt):
    segmentAddStarConf = _segmentConf.addUserStar
    pointIdList = segmentAddStarConf.get('pointIdList', [])
    maxCount = segmentAddStarConf.get('maxCount', 0)

    if evt.sharePointId not in pointIdList:
        return
    if SegmentMatchHelper.getUserSegmentInfo(evt.userId, 0).get('segment') >= 7:
        return
    clientId = sessiondata.getClientId(evt.userId)
    sharePoint = hall_share3.getSharePoint(HALL_GAMEID, evt.userId, clientId, evt.sharePointId)
    rewardCount, totalRewardCount = hall_share3.getRewardCount(evt.gameId, evt.userId, sharePoint,
                                                               pktimestamp.getCurrentTimestamp())
    if rewardCount >= maxCount:
        return

    leftCount = totalRewardCount - rewardCount
    if ftlog.is_debug():
        ftlog.debug('dizhu_segment_match._handleAddUserStar'
                    'userId=', evt.userId,
                    'gameId=', evt.gameId,
                    'sharePointId=', evt.sharePointId,
                    'rewardCount=', rewardCount,
                    'leftCount=', leftCount)
    msg = MsgPack()
    msg.setCmd('dizhu')
    msg.setResult('action', 'segment_add_star')
    msg.setResult('gameId', evt.gameId)
    msg.setResult('userId', evt.userId)

    success = SegmentMatchHelper.addUserStarsByOne(evt.userId)
    msg.setResult('success', success)
    msg.setResult('leftCount', leftCount)
    msg.setResult('segmentInfo', SegmentMatchHelper.getUserSegmentInfo(evt.userId, 0))
    router.sendToUser(msg, evt.userId)
    if ftlog.is_debug():
        ftlog.debug('dizhu_segment_match._handleAddUserStar'
                    'userId=', evt.userId,
                    'gameId=', evt.gameId,
                    'sharePointId=', evt.sharePointId,
                    'msg=', msg._ht)
    return


def _handleRecover(evt, recoverType):
    ''' 处理段位恢复 '''
    userRecoverData = SegmentMatchHelper.getUserSegmentRecoverData(evt.userId)
    if ftlog.is_debug():
        ftlog.debug('dizhu_segment_match.handleRecover userId=', evt.userId, 'gameId=', evt.gameId, 'recoverType', recoverType,
                    'userRecoverData=', userRecoverData.toDict())

    if recoverType == 'share':
        segmentRecoverConf = _segmentConf.segmentRecover
        pointIdList = segmentRecoverConf.get('share', {}).get('pointIdList', [])
        maxCount = segmentRecoverConf.get('share', {}).get('maxCount', 0)
        if evt.sharePointId not in pointIdList or userRecoverData.shareRecoverCount >= maxCount:
            ftlog.warn('dizhu_segment_match.handleRecover pointId not in conf pointId=', evt.sharePointId,
                       'userId=', evt.userId,
                       'userRecoverData=', userRecoverData.toDict())
            return
        userRecoverData.shareRecoverCount += 1

    if userRecoverData.active:
        # 加一颗星
        issue = SegmentMatchHelper.getCurrentIssue()
        if not issue:
            ftlog.warn('dizhu_segment_match.handleRecover issue=None userId=', evt.userId)
            return

        # 连胜不中断
        SegmentWinStreakTaskHelper.syncUserWinStreak(evt.userId)

        currentUserData = SegmentMatchHelper.getUserSegmentDataIssue(evt.userId, issue) or UserSegmentDataIssue()
        segmentConf = _segmentConf.getSegmentInfo(currentUserData.segment)
        # 加一颗星, 判断是否达到升段
        stars = segmentConf.stars
        if currentUserData.currentStar < stars:
            currentUserData.currentStar += 1
        else:
            if currentUserData.segment == len(_segmentConf.segments):
                currentUserData.currentStar += 1
            else:
                currentUserData.currentStar = 1
                currentUserData.segment += 1

        # 插入排行榜
        insertRanklist(issue, evt.userId, currentUserData.segment * 100 + currentUserData.currentStar, _segmentConf.rankRecordCount)
        # 获取排名
        rank = SegmentMatchHelper.getUserRealRank(evt.userId, issue)
        currentUserData.rank = rank
        # 保存用户信息
        SegmentMatchHelper.saveUserSegmentDataIssue(evt.userId, issue, currentUserData)

        userRecoverData.totalRecoverCount += 1
        userRecoverData.active = 0
        SegmentMatchHelper.saveUserSegmentRecoverData(evt.userId, userRecoverData)

        # 发送协议给客户端
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'segment_recover')
        msg.setResult('gameId', evt.gameId)
        msg.setResult('userId', evt.userId)
        msg.setResult('success', 1)
        router.sendToUser(msg, evt.userId)


class SegmentMatchHelper(object):
    '''
    段位赛管理器，获取排行榜以及个人用户信息等
    '''
    _freshTimestamp = 0
    _cachedRankList = {}

    @classmethod
    def getSeasonInfo(cls, issue=None):
        ''' 获取当前赛季信息，包括issueNum, seasonNum, poolRewards '''
        issueDate = datetime.datetime.now()
        if issue:
            issueDate = datetime.datetime.strptime(issue, '%Y%m%d')
        for seasonInfo in _segmentConf.seasonList:
            if seasonInfo.startTime <= issueDate <= seasonInfo.endTime:
                return seasonInfo
        return None

    @classmethod
    def getCurrentIssue(cls):
        currentSeasonInfo = cls.getSeasonInfo()
        if currentSeasonInfo:
            return currentSeasonInfo.issueNum
        return None

    @classmethod
    def saveUserSegmentRoundInfo(cls, userId, roundInfo):
        ''' 保存用户局信息, 最多保存30局 '''
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.saveUserSegmentRoundInfo userId=', userId,
                        'roundInfo=', roundInfo,
                        'roundInfoDict=', roundInfo.toDict())

        roundInfoList = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, buildUserSegmentRoundKey())
        if roundInfoList:
            roundInfoList = json.loads(roundInfoList)
        else:
            roundInfoList = []
        roundInfoList.append(roundInfo.toDict())
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, buildUserSegmentRoundKey(), json.dumps(roundInfoList[-_segmentConf.roundListCount:]))

    @classmethod
    def getUserSegmentRoundInfo(cls, userId):
        ''' 获取用户五维图 '''

        outCardSeconds = 0
        bombs = 0
        winCount = 0
        dizhuCount = 0
        leadWinCount = 0

        roundInfoList = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, buildUserSegmentRoundKey())
        if roundInfoList:
            roundInfoList = json.loads(roundInfoList)
            roundList = [UserSegmentRoundInfo().fromDict(d) for d in roundInfoList]
            for roundInfo in roundList:
                outCardSeconds += roundInfo.outCardSeconds
                bombs += roundInfo.bombs
                winCount += roundInfo.isWin
                dizhuCount += roundInfo.isDizhu
                leadWinCount += roundInfo.leadWin

        return {
            'outCardSeconds': outCardSeconds,
            'bombs': bombs,
            'winCount': winCount,
            'dizhuCount': dizhuCount,
            'leadWinCount': leadWinCount
        }, len(roundInfoList if roundInfoList else 0)

    @classmethod
    def saveUserSegmentDataTotal(cls, userId, data):
        ''' 保存用户天梯赛总信息 '''
        key = buildUserSegmentMatchKey()
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.saveUserSegmentDataTotal userId=', userId,
                        'key=', key,
                        'data=', data,
                        'dataDict=', data.toDict())
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(data.toDict()))

    @classmethod
    def getUserSegmentDataTotal(cls, userId):
        ''' 获取用户天梯赛总信息 '''
        key = buildUserSegmentMatchKey()
        data = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        if data:
            data = json.loads(data)
            return UserSegmentDataTotal().fromDict(data)
        return None


    @classmethod
    def saveUserSegmentDataIssue(cls, userId, issue, data):
        ''' 保存用户当前赛季信息 '''
        key = buildUserSegmentIssueInfo(issue)
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.saveUserSegmentDataIssue userId=', userId,
                        'key=', key,
                        'data=', data,
                        'dataDict=', data.toDict())
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(data.toDict()))

    @classmethod
    def getUserSegmentDataIssue(cls, userId, issue):
        ''' 获取用户当前赛季信息 '''
        key = buildUserSegmentIssueInfo(issue)
        data = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        if data:
            data = json.loads(data)
            return UserSegmentDataIssue().fromDict(data)
        return None

    @classmethod
    def getIssueStateList(cls):
        '''获取赛季状态列表'''
        key = buildIssueStateKey()
        data = daobase.executeRePlayCmd('get', key)
        if data:
            return json.loads(data)
        return []

    @classmethod
    def saveIssueToIssueStateList(cls, issueNum):
        '''保存赛季状态列表'''
        issues = cls.getIssueStateList()
        for issue in issues:
            if issue['issue'] == issueNum:
                return False

        issues.append({'issue': issueNum, 'state': 0})
        savedIssues = issues[:]
        if len(issues) > _segmentConf.saveRecordCount:
            removedIssues = issues[0:len(issues) - _segmentConf.saveRecordCount]
            for issueState in removedIssues:
                rankListKey = buildRankListKey(issueState['issue'])  # 排行榜
                rewardPoolKey = buildRewardsPoolKey(issueState['issue'])
                daobase.executeRePlayCmd('del', rankListKey)
                daobase.executeRePlayCmd('del', rewardPoolKey)
            savedIssues = issues[len(issues) - _segmentConf.saveRecordCount:]

        key = buildIssueStateKey()
        daobase.executeRePlayCmd('set', key, json.dumps(savedIssues))
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.saveIssueToIssueStateList issueNum=', issueNum,
                        'issues=', issues)
        return True

    @classmethod
    def updateIssueState(cls, issueNum, state):
        '''更新赛季状态列表'''
        issues = cls.getIssueStateList()
        for issue in issues:
            if issue['issue'] == issueNum:
                issue['state'] = state
                break
        daobase.executeRePlayCmd('set', buildIssueStateKey(), json.dumps(issues))


    @classmethod
    def getUserCacheRank(cls, userId, issue):
        ''' 获取用户缓存的排行 '''
        userInfoList = cls.getAllSegmentRankList(issue)
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.getUserCacheRank',
                        'userId=', userId,
                        'userInfoList=', userInfoList,
                        'issue=', issue)

        for rank, userInfo in enumerate(userInfoList, 1):
            if userInfo['userId'] == userId:
                if ftlog.is_debug():
                    ftlog.debug('SegmentMatchHelper.getUserCacheRank',
                                'userId=', userId,
                                'rank=', rank,
                                'issue=', issue)
                return rank
        return -1

    @classmethod
    def getUserRealRank(cls, userId, issue):
        ''' 获取实时排名 '''
        userIds = getRanklist(issue, 0, -1)
        for rank, uId in enumerate(userIds, 1):
            if uId == userId:
                return rank
        return -1

    @classmethod
    def getSegmentRankList(cls, issue, start, stop):
        if not issue:
            issue = cls.getCurrentIssue()
            if not issue:
                ftlog.warn('SegmentMatchHelper.getSegmentRankList issue=None')
                return [], start, stop

        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.getSegmentRankList',
                        'issue=', issue,
                        'start=', start,
                        'stop=', stop)

        if cls.needRefresh(issue):
            start = max(1, start)
            userIds = getRanklist(issue, 0, -1)
            ret = []
            for index, userId in enumerate(userIds, 1):
                userdata.checkUserData(userId)
                userIssueData = cls.getUserSegmentDataIssue(userId, issue) or UserSegmentDataIssue()
                udata = userIssueData.toDict()
                name, purl = pkuserdata.getAttrs(userId, ['name', 'purl'])
                udata['userId'] = userId
                udata['name'] = name
                udata['avatar'] = purl
                udata['rank'] = index
                udata['title'] = cls.getSegmentTitle(udata['segment'])
                ret.append(udata)
            cls._cachedRankList[issue] = ret
            cls._freshTimestamp = pktimestamp.getCurrentTimestamp() + _segmentConf.rankCacheTime
            if ftlog.is_debug():
                ftlog.debug('SegmentMatchHelper.getSegmentRankList',
                            'issue=', issue,
                            'start=', start,
                            'stop=', stop,
                            '_cachedRankList=', cls._cachedRankList,
                            'ret=', ret)
        return cls._cachedRankList[issue][start-1:stop], start, stop

    @classmethod
    def getAllSegmentRankList(cls, issue):
        if cls.needRefresh(issue):
            userIds = getRanklist(issue, 0, -1)
            ret = []
            for index, userId in enumerate(userIds, 1):
                userdata.checkUserData(userId)
                udata = cls.getUserSegmentDataIssue(userId, issue).toDict()
                name, purl = pkuserdata.getAttrs(userId, ['name', 'purl'])
                udata['userId'] = userId
                udata['name'] = name
                udata['avatar'] = purl
                udata['rank'] = index
                ret.append(udata)
            cls._cachedRankList[issue] = ret
            cls._freshTimestamp = pktimestamp.getCurrentTimestamp() + _segmentConf.rankCacheTime
        return cls._cachedRankList[issue]

    @classmethod
    def needRefresh(cls, issue):
        if issue not in cls._cachedRankList:
            return True

        if pktimestamp.getCurrentTimestamp() > cls._freshTimestamp:
            return True
        return False

    @classmethod
    def getSegmentMatchRules(cls):
        poolRewards = None
        seasonInfo = SegmentMatchHelper.getSeasonInfo()
        if seasonInfo:
            poolRewards = seasonInfo.poolRewards
        return {
            'segmentTips': _segmentConf.segmentTips,
            'seasonTips': _segmentConf.getSeasonTips(),
            'seasonRewards': _segmentConf.seasonRewards,
            'poolRewards': poolRewards,
            'startTime': seasonInfo.startTime.strftime('%Y.%m.%d'),
            'endTime': seasonInfo.endTime.strftime('%Y.%m.%d'),
            'issueNum': seasonInfo.issueNum,
            'seasonNum': seasonInfo.seasonNum
        }

    @classmethod
    def getSegmentTitle(cls, segment):
        ''' 获取段位文本描述 '''
        for segmentInfo in _segmentConf.segments:
            if segment == segmentInfo.segment:
                return segmentInfo.title
        return None

    @classmethod
    def getUserSegmentInfo(cls, userId, issue):
        ''' 获取用户信息接口，包括五维图以及胜率等总信息 '''
        # 获取当前赛季用户段位
        abilityList = None
        maxSegment = None
        maxWinStreak = None
        winRate = None
        starTime = None
        endTime = None
        hasPoolReward = None
        totalPlayCount = 0
        issue = issue or cls.getCurrentIssue()
        if not issue:
            ftlog.warn('SegmentMatchHelper.getUserSegmentInfo', 'userId=', userId, 'issue=', issue)
            return {
                'segment': None,
                'currentStar': None,
                'totalStar': None,
                'stars': None,
                'rank': None,
                'seasonNum': 0,
                'issueNum': None,
                'starTime': starTime,
                'endTime': endTime,
                'hasPoolReward': hasPoolReward,
                'maxSegment': maxSegment,
                'maxWinStreak': maxWinStreak,
                'winRate': winRate,
                'totalPlayCount': totalPlayCount,
                'abilityList': abilityList,
                'mainPicture': _segmentConf.getMainPicture(),
                'mainPicture2': _segmentConf.getMainPicture2()
            }

        userSegmentIssue = cls.getUserSegmentDataIssue(userId,  issue)

        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.getUserSegmentInfo userId=', userId,
                        'issue=', issue,
                        'userSegmentIssue=', userSegmentIssue.toDict() if userSegmentIssue else None)

        if not userSegmentIssue:
            # 判断段位继承， 获取用户最近赛季的issue
            issueStateList = SegmentMatchHelper.getIssueStateList()
            userSegmentIssue = UserSegmentDataIssue()
            userSegmentIssue.segment = 1
            if userId >= 10000:
                if issueStateList:
                    userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(userId, issueStateList[-1]['issue'])
                    if not userSegmentIssueHistory and len(issueStateList) > 1:
                        userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(userId, issueStateList[-2]['issue'])

                    if userSegmentIssueHistory and userSegmentIssueHistory.inherit:
                        userSegmentIssue.segment = userSegmentIssueHistory.inherit

                insertRanklist(issue, userId, userSegmentIssue.segment * 100 + userSegmentIssue.currentStar)
                # 获取排名
                rank = SegmentMatchHelper.getUserRealRank(userId, issue)
                userSegmentIssue.rank = rank
                seasonInfo = SegmentMatchHelper.getSeasonInfo(issue)
                if seasonInfo.poolRewards.get('type') == 'segment':
                    _addUserToRewardPool(seasonInfo, userId)
                # 保存用户信息
                SegmentMatchHelper.saveUserSegmentDataIssue(userId, issue, userSegmentIssue)

        # 获取用户总信息
        userTotalInfo = cls.getUserSegmentDataTotal(userId)
        if userTotalInfo:
            maxSegment = userTotalInfo.maxSegment
            totalPlayCount = userTotalInfo.totalPlayCount
            maxWinStreak = userTotalInfo.maxWinStreak
            try:
                winRate = '%d' % (userTotalInfo.totalWinCount * 1.0 / userTotalInfo.totalPlayCount * 100) + '%'
            except Exception, e:
                ftlog.error('SegmentMatchHelper.getUserSegmentInfo userId=', userId,
                            'issue=', issue,
                            'userTotalInfo=', userTotalInfo.toDict(),
                            'err=', e.message)
                winRate = '0%'

            # 获取五维图信息
            if totalPlayCount >= _segmentConf.roundListCount:
                userRoundInfo, length = cls.getUserSegmentRoundInfo(userId)
                # 计算局均出牌时间
                outSeconds = round(userRoundInfo['outCardSeconds'] * 1.0 / length, 2)
                if outSeconds >= 60:
                    outcardRate = 0
                elif outSeconds <= 15:
                    outcardRate = 1
                else:
                    outcardRate = 1 - (round((outSeconds - 15) * 1.0 / 45, 2))

                # 计算局均炸弹数
                bombs = round(userRoundInfo['bombs'] * 1.0 / length, 2)
                if bombs >= 1.2:
                    boomRate = 1
                elif bombs <= 0.1:
                    boomRate = 0
                else:
                    boomRate = round((bombs - 0.1) * 1.0 / 1.1, 2)

                abilityList = [round(userRoundInfo['winCount'] * 1.0 / length, 2),
                               outcardRate,
                               boomRate,
                               round(userRoundInfo['leadWinCount'] * 1.0 / length, 2),
                               round(userRoundInfo['dizhuCount'] * 1.0 / length, 2)
                               ]
        seasonNum = None
        seasonInfo = cls.getSeasonInfo()
        if seasonInfo:
            seasonNum = seasonInfo.seasonNum
            starTime = seasonInfo.startTime.strftime('%Y-%d-%m')
            endTime = seasonInfo.endTime.strftime('%Y-%d-%m')
            hasPoolReward = True if seasonInfo.poolRewards else False

        stars = None
        issueNum = 0

        segmentInfo = _segmentConf.getSegmentInfo(userSegmentIssue.segment)
        if seasonInfo:
            stars = segmentInfo.stars
            issueNum = seasonInfo.issueNum
        return {
            'segment': userSegmentIssue.segment,
            'currentStar': userSegmentIssue.currentStar,
            'totalStar': userSegmentIssue.segment * 100 + userSegmentIssue.currentStar,
            'stars': stars,
            'rank': SegmentMatchHelper.getUserRealRank(userId, issue),
            'seasonNum': seasonNum,
            'issueNum': int(issueNum),
            'maxSegment': maxSegment,
            'maxWinStreak': maxWinStreak,
            'starTime': starTime,
            'endTime': endTime,
            'hasPoolReward': hasPoolReward,
            'winRate': winRate,
            'totalPlayCount': totalPlayCount,
            'totalWinCount': userTotalInfo.totalWinCount if userTotalInfo else 0,
            'abilityList': abilityList,
            'mainPicture': _segmentConf.getMainPicture(),
            'mainPicture2': _segmentConf.getMainPicture2()
        }

    @classmethod
    def saveUserSegmentRecoverData(cls, userId, data):
        ''' 保存段位复活数据 '''
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.saveUserSegmentRecoverData userId=', userId,
                        'data=', data.toDict())
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, buildUserSegmentRecoverKey(), json.dumps(data.toDict()))

    @classmethod
    def getUserSegmentRecoverData(cls, userId):
        ''' 获取段位复活数据 '''
        data = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, buildUserSegmentRecoverKey())
        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.getUserSegmentRecoverData userId=', userId,
                        'data=', json.loads(data) if data else None)
        if data:
            return UserSegmentRecoverData().fromDict(json.loads(data))
        else:
            return UserSegmentRecoverData()

    @classmethod
    def processUserSegmentIssues(cls, userId, issue):
        ''' 处理用户过期数据 '''
        key = buildUserSegmentIssues()
        issueList = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        if issueList:
            issueList = json.loads(issueList)
        else:
            issueList = []
        if issue in issueList:
            return
        issueList.append(issue)
        savedIssues = issueList[:]
        if len(issueList) > _segmentConf.saveRecordCount:
            removedIssues = issueList[0:len(issueList) - _segmentConf.saveRecordCount]
            for isue in removedIssues:
                delKey = buildUserSegmentIssueInfo(isue)  # 具体赛季信息
                segmentdata.delSegmentAttr(userId, DIZHU_GAMEID, delKey)
            savedIssues = issueList[len(issueList) - _segmentConf.saveRecordCount:]
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(savedIssues))

    @classmethod
    def addUserSegmentTableWinRewardCount(cls, userId, count):
        '''存储用户牌桌奖励目前获得的数量'''
        key = buildUserSegmentTableWinRewardKey()
        info = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        currentTimestamp = pktimestamp.getCurrentTimestamp()
        if info:
            info = json.loads(info)
        else:
            info = {'count': 0, 'timestamp': currentTimestamp}

        if not pktimestamp.is_same_day(info['timestamp'], currentTimestamp):
            info = {'count': 0, 'timestamp': currentTimestamp}

        if ftlog.is_debug():
            ftlog.debug('SegmentMatchHelper.addUserSegmentTableWinRewardCount userId=', userId, 'count=', count,
                        'info=', info)

        if info['count'] >= _segmentConf.gameWinReward.get('totalLimit', -1):
            return False
        info['count'] += count

        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(info))
        return True

    @classmethod
    def addUserStarsByOne(cls, userId):
        ''' 增加用户星数 '''
        global _segmentConf

        # 添加赛季到赛季列表
        issue = SegmentMatchHelper.getCurrentIssue()
        if not issue:
            ftlog.warn('SegmentMatchHelper.addUserStarsByOne',
                       'userId=', userId,
                       'issue=', issue)
            return 0

        # 当前赛季用户信息处理
        currentUserData = SegmentMatchHelper.getUserSegmentDataIssue(userId, issue)
        if not currentUserData:
            currentUserData = UserSegmentDataIssue()
            issueStateList = SegmentMatchHelper.getIssueStateList()
            currentUserData.segment = 1
            if userId >= 10000:
                if issueStateList:
                    userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(userId, issueStateList[-1]['issue'])
                    if not userSegmentIssueHistory and len(issueStateList) > 1:
                        userSegmentIssueHistory = SegmentMatchHelper.getUserSegmentDataIssue(userId, issueStateList[-2]['issue'])

                    if userSegmentIssueHistory and userSegmentIssueHistory.inherit:
                        currentUserData.segment = userSegmentIssueHistory.inherit

        segmentConf = _segmentConf.getSegmentInfo(currentUserData.segment)

        isLevelUp = False

        # 加一颗星, 判断是否达到升段
        stars = segmentConf.stars
        if currentUserData.currentStar < stars:
            currentUserData.currentStar += 1
        else:
            if currentUserData.segment == len(_segmentConf.segments):
                currentUserData.currentStar += 1
            else:
                currentUserData.currentStar = 1
                currentUserData.segment += 1
                isLevelUp = True

        # 插入排行榜
        insertRanklist(issue, userId, currentUserData.segment * 100 + currentUserData.currentStar, _segmentConf.rankRecordCount)
        # 获取排名
        rank = SegmentMatchHelper.getUserRealRank(userId, issue)
        currentUserData.rank = rank
        # 段位继承
        currentUserData.inherit = _segmentConf.getSegmentInfo(currentUserData.segment).inherit
        # 保存用户信息
        SegmentMatchHelper.saveUserSegmentDataIssue(userId, issue, currentUserData)

        # 总用户信息处理
        userDataTotal = SegmentMatchHelper.getUserSegmentDataTotal(userId)
        if not userDataTotal:
            userDataTotal = UserSegmentDataTotal()

        userDataTotal.maxSegment = max(userDataTotal.maxSegment, currentUserData.segment)

        # 印记
        userDataTotal.legendCount += 1 if isLevelUp and currentUserData.segment == len(_segmentConf.segments) else 0
        SegmentMatchHelper.saveUserSegmentDataTotal(userId, userDataTotal)

        # 瓜分奖池
        seasonInfo = SegmentMatchHelper.getSeasonInfo(issue)
        if seasonInfo.poolRewards.get('type') == 'segment':
            _addUserToRewardPool(seasonInfo, userId)
        return 1


class SegmentWinStreakData(object):
    ''' 连胜任务系统 '''

    def __init__(self, userId):
        self.userId = userId
        self.winStreak = 0  # 当前连胜
        self.winStreakBackUp = 0  # 连胜的备份

    def fromDict(self, d):
        self.winStreak = d.get('winStreak', 0)
        self.winStreakBackUp = d.get('winStreakBackUp', 0)
        return self

    def toDict(self):
        return {
            'winStreak': self.winStreak,
            'winStreakBackUp': self.winStreakBackUp
        }


class SegmentWinStreakTaskHelper(object):
    ''' 连胜任务相关 '''
    @classmethod
    def isActive(cls):
        return bool(_segmentConf.tableWinStreakTask)

    @classmethod
    def getUserProgressInfo(cls, userId):
        ''' 获取用户当前的任务进度 '''
        key = buildUserSegmentWinStreakTaskKey()
        dataStr = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        if dataStr:
            userData = SegmentWinStreakData(userId).fromDict(json.loads(dataStr))
        else:
            userData = SegmentWinStreakData(userId).fromDict({})

        # 获取任务总进度及其奖励
        for progressInfo in _segmentConf.tableWinStreakTask:
            if progressInfo.get('progress', 0)  > userData.winStreak:
                return userData, progressInfo, _segmentConf.tableWinStreakTask
        return SegmentWinStreakData(userId), _segmentConf.tableWinStreakTask[0] if _segmentConf.tableWinStreakTask else [], _segmentConf.tableWinStreakTask if _segmentConf.tableWinStreakTask else []

    @classmethod
    def getUserWinStreak(cls, userId):
        ''' 获取用户当前的连胜数量 '''
        key = buildUserSegmentWinStreakTaskKey()
        dataStr = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, key)
        if dataStr:
            userData = SegmentWinStreakData(userId).fromDict(json.loads(dataStr))
        else:
            userData = SegmentWinStreakData(userId).fromDict({})
        return userData.winStreak

    @classmethod
    def updateUserWinStreak(cls, userId, isWin, punishState):
        ''' 增加奖励次数， 达到要求要发奖且重置 '''
        userData, progressInfo, _ = cls.getUserProgressInfo(userId)
        currentWinStreak = userData.winStreak
        if isWin and progressInfo:
            userData.winStreak += 1
            userData.winStreakBackUp = userData.winStreak
            currentWinStreak += 1
            rewards = None
            isAsync = None
            if userData.winStreak == progressInfo.get('progress', 0):
                # 发奖
                rewards = progressInfo.get('rewards', [])

                # 分享后才能发奖
                winStreakRewardSwitch = WxShareControlHelper.getWinStreakRewardSwitch()
                isAsync = progressInfo.get('params', {}).get('isAsync') and winStreakRewardSwitch
                if not isAsync:
                    contentItems = TYContentItem.decodeList(rewards)
                    from dizhu.entity import dizhu_util
                    dizhu_util.sendRewardItems(userId, contentItems, None, 'DIZHU_SEGMENT_MATCH_WINSTREAK', userData.winStreak)
                    ftlog.info('dizhu_segment_match.settlementRanking',
                               'userId=', userId,
                               'winStreak=', userData.winStreak,
                               'segmentRewards=', rewards)

                # 达到最大连胜数
                if userData.winStreak == _segmentConf.tableWinStreakTask[-1].get('progress'):
                    userData.winStreak = 0
                    userData.winStreakBackUp = 0

                if not isAsync:
                    for winStreakReward in rewards:
                        # 如果是红包券则广播红包券事件
                        if winStreakReward['itemId'] == 'user:coupon':
                            from hall.game import TGHall
                            TGHall.getEventBus().publishEvent(
                                UserCouponReceiveEvent(HALL_GAMEID, userId, winStreakReward['count'], user_coupon_details.USER_COUPON_SOURCE_SEGMENT_WINSTREAK_TASK))

            # 保存用户数据
            key = buildUserSegmentWinStreakTaskKey()
            dataStr = json.dumps(userData.toDict())
            segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, dataStr)
            return userData, rewards, currentWinStreak, isAsync
        else:
            if punishState != 2:
                userData.winStreak = 0
                key = buildUserSegmentWinStreakTaskKey()
                segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(userData.toDict()))
            return userData, None, userData.winStreak, None

    @classmethod
    def syncUserWinStreak(cls, userId):
        key = buildUserSegmentWinStreakTaskKey()
        userData, _, _ = cls.getUserProgressInfo(userId)
        userData.winStreak = userData.winStreakBackUp
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(userData.toDict()))

    @classmethod
    def syncUserWinStreakBackUp(cls, userId):
        key = buildUserSegmentWinStreakTaskKey()
        userData, _, _ = cls.getUserProgressInfo(userId)
        userData.winStreakBackUp = userData.winStreak
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, key, json.dumps(userData.toDict()))
