# -*- coding:utf-8 -*-
'''
Created on 2018-05-11

@author: wangyonghui
'''
import freetime.util.log as ftlog
from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper
from hall.entity.hallusercond import UserConditionRegister, UserCondition
from poker.entity.biz.exceptions import TYBizConfException


class UserConditionSegment(UserCondition):
    TYPE_ID = 'user.cond.segment'

    def __init__(self):
        super(UserConditionSegment, self).__init__()
        self.startSegment = None
        self.endSegment = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        issue = SegmentMatchHelper.getCurrentIssue()
        if not issue:
            return False
        currentUserData = SegmentMatchHelper.getUserSegmentDataIssue(userId, issue)
        if not currentUserData:
            return False
        segment = currentUserData.segment
        if (self.startSegment == -1 or segment >= self.startSegment) and (self.endSegment == -1 or segment <= self.endSegment):
            return True
        return False

    def decodeFromDict(self, d):
        self.startSegment = d.get('startSegment')
        if not isinstance(self.startSegment, int):
            raise TYBizConfException(d, 'UserConditionSegment.startSegment must be int')

        self.endSegment = d.get('endSegment')
        if not isinstance(self.endSegment, int):
            raise TYBizConfException(d, 'UserConditionSegment.endSegment must be int')
        return self


class UserConditionSegmentRewardPool(UserCondition):

    TYPE_ID = 'user.cond.segmentRewardPool'

    def __init__(self):
        super(UserConditionSegmentRewardPool, self).__init__()
        self.startSegment = None
        self.endSegment = None
        self.rankLimit = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        segment = kwargs.get('segment')
        rank = kwargs.get('rank')
        if ftlog.is_debug():
            ftlog.debug('UserConditionSegmentRewardPool.check userId=', userId,
                        'gameId=', gameId,
                        'clientId=', clientId,
                        'timestamp=', timestamp,
                        'startSegment=', self.startSegment,
                        'endSegment=', self.endSegment,
                        'rankLimit=', self.rankLimit,
                        'kwargs=', kwargs)

        if self.startSegment != -1 and segment < self.startSegment:
            return False

        if self.endSegment != -1 and segment > self.endSegment:
            return False

        if self.rankLimit != -1 and rank > self.rankLimit:
            return False
        return True

    def decodeFromDict(self, d):
        self.startSegment = d.get('startSegment')
        if not isinstance(self.startSegment, int):
            raise TYBizConfException(d, 'UserConditionSegmentRewardPool.startSegment must be int')

        self.endSegment = d.get('endSegment')
        if not isinstance(self.endSegment, int):
            raise TYBizConfException(d, 'UserConditionSegmentRewardPool.endSegment must be int')

        self.rankLimit = d.get('rankLimit')
        if not isinstance(self.rankLimit, int):
            raise TYBizConfException(d, 'UserConditionSegmentRewardPool.rankLimit must be int')

        return self


class UserConditionSegmentWinDoubles(UserCondition):

    TYPE_ID = 'user.cond.segmentWinDoubles'

    def __init__(self):
        super(UserConditionSegmentWinDoubles, self).__init__()
        self.start = None
        self.end = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        winlose = kwargs.get('winlose')
        if ftlog.is_debug():
            ftlog.debug('UserConditionSegmentWinDoubles.check userId=', userId,
                        'gameId=', gameId,
                        'clientId=', clientId,
                        'timestamp=', timestamp,
                        'doubles=', winlose.windoubles)

        if (self.start == -1 or winlose.windoubles >= self.start) and (self.end == -1 or winlose.windoubles <= self.end):
            return True
        return False

    def decodeFromDict(self, d):
        self.start = d.get('start')
        if not isinstance(self.start, int):
            raise TYBizConfException(d, 'UserConditionSegmentWinDoubles.start must be int')

        self.end = d.get('end')
        if not isinstance(self.end, int):
            raise TYBizConfException(d, 'UserConditionSegmentWinDoubles.end must be int')
        return self


class UserConditionSegmentChuntian(UserCondition):

    TYPE_ID = 'user.cond.segmentChuntian'

    def __init__(self):
        super(UserConditionSegmentChuntian, self).__init__()

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        winlose = kwargs.get('winlose')
        if ftlog.is_debug():
            ftlog.debug('UserConditionSegmentChuntian.check userId=', userId,
                        'gameId=', gameId,
                        'clientId=', clientId,
                        'timestamp=', timestamp,
                        'isChuntian=', winlose.chunTian)

        if winlose.chunTian:
            return True
        return False

    def decodeFromDict(self, d):
        return self


class UserConditionCouponWithdraw(UserCondition):

    TYPE_ID = 'user.cond.couponWithdraw'

    def __init__(self):
        super(UserConditionCouponWithdraw, self).__init__()
        self.start = None
        self.stop = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        from hall.entity import hallexchange
        count = len([record for record in hallexchange.getExchangeRecords(userId)
                     if record.state == hallexchange.TYExchangeRecord.STATE_SHIPPING_SUCC])
        if ftlog.is_debug():
            ftlog.debug('UserConditionCouponWithdraw.check userId=', userId,
                        'gameId=', gameId,
                        'clientId=', clientId,
                        'timestamp=', timestamp,
                        'count', count)

        if (count >= self.start) and (self.stop == -1 or count <= self.stop):
            return True
        return False

    def decodeFromDict(self, d):
        self.start = d.get('start')
        if not isinstance(self.start, int):
            raise TYBizConfException(d, 'UserConditionCouponWithdraw.start must be int')

        self.stop = d.get('stop')
        if not isinstance(self.stop, int):
            raise TYBizConfException(d, 'UserConditionCouponWithdraw.end must be int')
        return self


def _registerClasses():
    ftlog.debug('dizhu_segment_usercond._registerClasses')
    UserConditionRegister.registerClass(UserConditionSegmentRewardPool.TYPE_ID, UserConditionSegmentRewardPool)
    UserConditionRegister.registerClass(UserConditionSegmentWinDoubles.TYPE_ID, UserConditionSegmentWinDoubles)
    UserConditionRegister.registerClass(UserConditionSegmentChuntian.TYPE_ID, UserConditionSegmentChuntian)
    UserConditionRegister.registerClass(UserConditionCouponWithdraw.TYPE_ID, UserConditionCouponWithdraw)
    UserConditionRegister.registerClass(UserConditionSegment.TYPE_ID, UserConditionSegment)
