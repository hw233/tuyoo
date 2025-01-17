# -*- coding:utf-8 -*-
'''
Created on 2018年7月23日

@author: wangyonghui
'''
import json

import datetime

from dizhu.entity import dizhu_util
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.reward_async.dao import rewards_async_dao
from dizhu.entity.reward_async.events import UserRewardAsyncEvent
from dizhu.games import matchutil
from freetime.entity.msg import MsgPack
from hall.entity.hallconf import HALL_GAMEID
from hall.entity.usercoupon import user_coupon_details
from hall.entity.usercoupon.events import UserCouponReceiveEvent
from poker.entity.biz.content import TYContentItem
from poker.entity.dao import daobase, daoconst
import poker.util.timestamp as pktimestamp
import freetime.util.log as ftlog


# 分享获取奖励类型
REWARD_ASYNC_TYPE_AS_ARENA_MATCH = 'arenaMatch'  # 红包赛奖励
REWARD_ASYNC_TYPE_AS_WINSTREAK = 'winStreak'  # 连胜奖励


class RewardIdGenRedis(object):
    ''' 奖励ID生成器 '''
    @classmethod
    def genRewardId(cls, nowTimestamp):
        cls.updateRewardIdInfo(nowTimestamp)
        return daobase.executeRePlayCmd('HINCRBY', 'reward.id.number', 'number', 1)

    @classmethod
    def updateRewardIdInfo(cls, nowTimestamp):
        ''' ID 从 1000001 开始 '''
        timstamp = int(daobase.executeRePlayCmd('HGET', 'reward.id.number', 'timestamp') or 0)
        if not pktimestamp.is_same_day(nowTimestamp, timstamp):
            daobase.executeRePlayCmd('HSET', 'reward.id.number', 'number', 1000000)
            daobase.executeRePlayCmd('HSET', 'reward.id.number', 'timestamp', nowTimestamp)


class RewardAsyncHelper(object):
    ''' 数据管理以及接口处理 '''
    @classmethod
    def genRewardId(cls):
        ''' 生成奖励唯一ID '''
        nowTimeStamp = pktimestamp.getCurrentTimestamp()
        intId = RewardIdGenRedis.genRewardId(nowTimeStamp)
        ret = datetime.datetime.fromtimestamp(nowTimeStamp).strftime('%Y%m%d') + str(intId)
        return ret

    @classmethod
    def getRewardByRewardId(cls, userId, rewardId):
        '''
        获取用户所有奖励, 这里会删除已经领过的奖励
        {
            "type": "arenaMatch",
            "rewards": [{"itemId": "user:chip", "count": 100}],
            "rewardId": "20170723000001",
            "timestamp": 1532113511,
            "params": {}
        }
        '''
        ret = None
        saveList = []
        userRewards = rewards_async_dao.getRewardAsync(userId, DIZHU_GAMEID) or []
        if ftlog.is_debug():
            ftlog.debug('RewardAsyncHelper.getRewardByRewardId userId=', userId,
                        'rewardId=', rewardId,
                        'userRewards=', userRewards)
        if userRewards:
            userRewards = json.loads(userRewards)
            for rewardInfo in userRewards:
                if rewardInfo['rewardId'] == rewardId:
                    ret = rewardInfo
                    continue
                saveList.append(rewardInfo)
        rewards_async_dao.setRewardAsync(userId, DIZHU_GAMEID, json.dumps(saveList))
        if ftlog.is_debug():
            ftlog.debug('RewardAsyncHelper.getRewardByRewardId userId=', userId,
                        'rewardId=', rewardId,
                        'reward=', ret)
        return ret

    @classmethod
    def buildGetRewardResponse(cls, userId, rewardId):
        ''' 返回客户端消息 mo '''
        ret = cls.getRewardByRewardId(userId, rewardId)
        if ret:
            rewards = ret['rewards']
            rewardType = ret['type']
            # 给用户发奖
            contentItems = TYContentItem.decodeList(rewards)
            if rewardType == REWARD_ASYNC_TYPE_AS_ARENA_MATCH:
                matchId = ret.get('params', {}).get('matchId', 0)
                mixId = ret.get('params', {}).get('mixId', 0)
                rank = ret.get('params', {}).get('rank', 0)
                sequence = ret.get('params', {}).get('sequence', 0)
                roomName = ret.get('params', {}).get('roomName', '红包赛')

                mail = '红包赛奖励#恭喜您在%s' % roomName + '中, 获得${rewardContent}。'
                dizhu_util.sendRewardItems(userId, contentItems, mail,
                                           'MATCH_REWARD', ret.get('params', {}).get('matchId', 0))
                for reward in rewards:
                    chipType = matchutil.getBiChipType(reward['itemId'])
                    kindId = 0
                    if chipType == daoconst.CHIP_TYPE_ITEM:
                        kindId = reward['itemId'].strip('item:')
                    matchutil.report_bi_game_event('MATCH_REWARD', userId, matchId, 0, sequence, 0, 0, 0,
                                                   [chipType, reward['count'], kindId, rank, mixId, len(rewards)],
                                                   'match_reward')
            elif rewardType == REWARD_ASYNC_TYPE_AS_WINSTREAK:
                winStreak = ret.get('params', {}).get('winStreak', 0)
                dizhu_util.sendRewardItems(userId, contentItems, None, 'DIZHU_SEGMENT_MATCH_WINSTREAK', winStreak)

            # 如果是奖券则广播奖券事件
            for reward in rewards:
                if reward['itemId'] == 'user:coupon':
                    if rewardType == REWARD_ASYNC_TYPE_AS_ARENA_MATCH:
                        from hall.game import TGHall
                        TGHall.getEventBus().publishEvent(
                            UserCouponReceiveEvent(HALL_GAMEID, userId, reward['count'], user_coupon_details.USER_COUPON_SOURCE_MATCH_ARENA))

                    elif rewardType == REWARD_ASYNC_TYPE_AS_WINSTREAK:
                        from hall.game import TGHall
                        TGHall.getEventBus().publishEvent(
                            UserCouponReceiveEvent(HALL_GAMEID, userId, reward['count'], user_coupon_details.USER_COUPON_SOURCE_SEGMENT_WINSTREAK_TASK))
        mo = MsgPack()
        mo.setCmd('dizhu')
        mo.setResult('action', 'get_reward_async')
        mo.setResult('gameId', DIZHU_GAMEID)
        mo.setResult('userId', userId)
        mo.setResult('rewardInfo', ret)
        return mo

    @classmethod
    def getAllUserRewards(cls, userId):
        '''
        获取用户所有奖励
        {
            "type": "arenaMatch",
            "rewards": [{"itemId": "user:chip", "count": 100}],
            "rewardId": "20170723000001",
            "timestamp": 1532113511,
            "params": {}
        }
        这里会删除已经过期的奖励
        '''
        ret = []
        userRewards = rewards_async_dao.getRewardAsync(userId, DIZHU_GAMEID) or []
        if userRewards:
            userRewards = json.loads(userRewards)
            for rewardInfo in userRewards:
                if pktimestamp.getCurrentTimestamp() - rewardInfo['timestamp'] > 24 * 60 * 60 * 7:
                    continue
                ret.append(rewardInfo)

        rewards_async_dao.setRewardAsync(userId, DIZHU_GAMEID, json.dumps(ret))
        if ftlog.is_debug():
            ftlog.debug('RewardAsyncHelper.getAllUserRewards userId=', userId,
                        'rewards=', ret)
        return ret

    @classmethod
    def addUserRewards(cls, userId, rewardInfo):
        ''' 保存用户奖励 '''
        rewards = cls.getAllUserRewards(userId)
        rewards.append(rewardInfo)
        rewards_async_dao.setRewardAsync(userId, DIZHU_GAMEID, json.dumps(rewards))
        if ftlog.is_debug():
            ftlog.debug('RewardAsyncHelper.addUserRewards userId=', userId,
                        'reward=', rewardInfo)


def subscribeUserRewardAsyncEvent():
    from dizhu.game import TGDizhu
    TGDizhu.getEventBus().subscribe(UserRewardAsyncEvent, _processUserRewardAsync)


def _processUserRewardAsync(evt):
    rewardInfo = {
        'type': evt.rewardType,
        'rewards': evt.rewards,
        'rewardId': evt.rewardId,
        'timestamp': evt.timestamp,
        'params': evt.params
    }
    if ftlog.is_debug():
        ftlog.debug('reward_async._processUserRewardAsync userId=', evt.userId,
                    'evt=', rewardInfo)
    if evt.rewardType == REWARD_ASYNC_TYPE_AS_ARENA_MATCH:
        from dizhu.game import TGDizhu
        from dizhu.entity.common.events import ActiveEvent
        TGDizhu.getEventBus().publishEvent(ActiveEvent(6, evt.userId, 'redEnvelope'))
    RewardAsyncHelper.addUserRewards(evt.userId, rewardInfo)


def _initialize():
    ftlog.info('reward_async._initialize begin')
    subscribeUserRewardAsyncEvent()
    ftlog.info('reward_async._initialize end')
