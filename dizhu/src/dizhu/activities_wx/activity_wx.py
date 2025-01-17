# -*- coding:utf-8 -*-
'''
Created on 2018-08-20

@author: wangyonghui
'''
from sre_compile import isstring

import datetime
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from poker.entity.biz.confobj import TYConfable, TYConfableRegister
from poker.entity.biz.exceptions import TYBizConfException
import poker.entity.events.tyeventbus as pkeventbus
import freetime.util.log as ftlog
from poker.entity.configure import configure as pkconfigure, configure
from poker.entity.events.tyevent import EventConfigure
import poker.util.timestamp as pktimestamp


class ActivityWxException(Exception):
    def __init__(self, errCode, errMsg):
        super(ActivityWxException, self).__init__(errCode, errMsg)

    @property
    def errCode(self):
        return self.args[0]

    @property
    def errMsg(self):
        return self.args[1]


class ActivityWxRegister(TYConfableRegister):
    _typeid_clz_map = {}


class ActivityWx(TYConfable):
    TYPE_ID = 'unknown'

    def __init__(self):
        super(ActivityWx, self).__init__()
        self._actId = None  # 活动ID字符串类型，允许重复
        self._intActId = None  # 用于区分相同 actId 的情况
        self._startTime = None  # 活动开始时间
        self._endTime = None  # 活动结束时间

    @property
    def actId(self):
        return self._actId

    @property
    def intActId(self):
        return self._intActId

    @property
    def startTime(self):
        return self._startTime

    @property
    def endTime(self):
        return self._endTime

    def isExpired(self, timestamp):
        if ftlog.is_debug():
            ftlog.debug('ActivityWx.isExpired actId=', self.actId,
                        'statTime=', self._startTime,
                        'endTime=', self.endTime)
        nowDT = datetime.datetime.fromtimestamp(timestamp)
        if not self._startTime or not self._endTime:
            return 0

        if self._startTime <= nowDT <= self._endTime:
            return 0
        return 1

    def init(self):
        pass

    def cleanup(self):
        pass

    def decodeFromDict(self, d):
        self._actId = d.get('actId')
        if not self._actId or not isstring(self._actId):
            raise TYBizConfException(d, 'actId must not empty string')

        self._intActId = d.get('intActId', 0)
        if not isinstance(self._intActId, int) or self._intActId < 0:
            raise TYBizConfException(d, 'intActId must int >= 0')

        startTime = d.get('startTime')
        if startTime is not None:
            startTime = datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S')

        endTime = d.get('endTime')
        if endTime is not None:
            endTime = datetime.datetime.strptime(endTime, '%Y-%m-%d %H:%M:%S')

        self._startTime = startTime
        self._endTime = endTime

        self._decodeFromDictImpl(d)
        return self

    def _decodeFromDictImpl(self, d):
        return self

    def handleActivityRequest(self, userId, clientId, msg):
        pass


_inited = False
# key=actId, value=ActivityWx
_activities = {}


def _initActivities(activities):
    for act in activities.values():
        try:
            act.init()
        except Exception, e:
            ftlog.error('activity_wx._initActivities actId=', act.actId, 'err=', e.message)
            _cleanupActivities(activities)


def _cleanupActivities(activities):
    for act in activities.values():
        try:
            act.cleanup()
        except Exception as e:
            ftlog.error('activity_wx._cleanupActivities actId=', act.actId, 'err=', e.message)


def _reloadConf():
    global _activities
    activities = {}
    conf = pkconfigure.getGameJson(DIZHU_GAMEID, 'activity.wx', {})
    for actConf in conf.get('activities', []):
        act = ActivityWxRegister.decodeFromDict(actConf)
        if act.actId in activities:
            raise TYBizConfException(actConf, 'duplicate actId: %s' % act.actId)
        # if act.isExpired(pktimestamp.getCurrentTimestamp()):
        #     ftlog.info('activity_wx._reloadConf expired actId=', act.actId)
        #     continue
        activities[act.actId] = act

    try:
        _cleanupActivities(_activities)
        _initActivities(activities)
        _activities = activities
        ftlog.info('activity_wx._reloadConf actIds=', _activities.keys())
    except Exception as e:
        ftlog.error('activity_wx._reloadConf err=', e.message)


def _onConfChanged(event):
    if _inited and event.isChanged(['game:6:activity.wx:0']):
        ftlog.info('activity_wx._onConfChanged')
        _reloadConf()


def _initialize():
    global _inited
    if not _inited:
        _inited = True
        _reloadConf()
        pkeventbus.globalEventBus.subscribe(EventConfigure, _onConfChanged)


class ActivityWxHelper(object):
    @classmethod
    def findActivity(cls, actId):
        return _activities.get(actId)

    @classmethod
    def getActivityList(cls, userId, clientId):
        ''' 获取活动列表 '''
        actIdList = configure.getTcContentByGameId('activity.wx', None, DIZHU_GAMEID, clientId, {})
        activityList = []
        for act in actIdList:
            actObj = cls.findActivity(act['actId'])
            if not actObj:
                continue
            if actObj.isExpired(pktimestamp.getCurrentTimestamp()):
                continue
            hasReward = actObj.hasReward(userId)
            act.update({'hasReward': hasReward})
            activityList.append(act)

        if ftlog.is_debug():
            ftlog.debug('ActivityWxHelper.getActivityList.userId=', userId,
                        'clientId=', clientId,
                        'activityList=', activityList)
        return activityList

    @classmethod
    def handleActivityRequest(cls, userId, clientId, actId, action, msg):
        '''
        处理活动请求, result, errmsg
        '''
        if not actId:
            raise ActivityWxException(-1, 'activity does not exist！')
        actObj = cls.findActivity(actId)
        if not actObj:
            raise ActivityWxException(-2, 'activity does not exist！')
        if actObj.isExpired(pktimestamp.getCurrentTimestamp()):
            raise ActivityWxException(-3, 'activity expired！')
        return actObj.handleRequest(userId, clientId, action, msg)
