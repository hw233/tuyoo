# -*- coding=utf-8
'''
Created on 2018年4月13日

@author: wangyonghui
'''

# 用户段位相关远程调
from dizhu.entity import dizhuconf
from dizhu.entity.official_counts import wx_official
from dizhu.entity.official_counts.events import OfficialMessageEvent
from dizhu.entity.reward_async.events import UserRewardAsyncEvent
from dizhu.entity.reward_async.reward_async import RewardAsyncHelper, REWARD_ASYNC_TYPE_AS_WINSTREAK
from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper, getSegmentConf, SegmentWinStreakTaskHelper
from dizhu.entity.segment.dizhu_segment_rewards import DizhuSegmentRewardsHelper
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.treasure_chest.events import TreasureChestEvent
from dizhu.entity.treasure_chest.treasure_chest import TreasureChestHelper, TREASURE_CHEST_TYPE_AS_WINSTREAK
from dizhu.games.segmentmatch.events import SegmentTableWinloseEvent
from dizhucomm.entity.events import Winlose
from hall.entity import hallitem
from hall.entity.hallconf import HALL_GAMEID
from poker.entity.configure import configure
from poker.protocol.rpccore import markRpcCall
import poker.util.timestamp as pktimestamp
import freetime.util.log as ftlog


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def processSegmentTableWinlose(roomId, tableId, userId, isWin, isDizhu, winUserId,
                         winlose, finalTableChip, winDoubles, bomb, chuntian,
                         winslam, topValidCard, baseScore, punishState=0, outCardSeconds=0, leadWin=0, **kwargs):

    from dizhu.game import TGDizhu
    from hall.game import TGHall
    ebus = TGDizhu.getEventBus()
    hallBus = TGHall.getEventBus()
    assist = kwargs.get('assist', 0)
    validMaxOutCard = kwargs.get('validMaxOutCard', 0)
    if ftlog.is_debug():
        ftlog.debug('processSegmentTableWinlose userId=', userId,
                    'assist', assist,
                    'validMaxOutCard', validMaxOutCard)
    winloseObj = Winlose(winUserId, topValidCard, isWin, isDizhu, winlose, finalTableChip, winDoubles, bomb, chuntian > 1,
                         winslam, baseScore, punishState=punishState, outCardSeconds=outCardSeconds, leadWin=leadWin,
                         assist=assist, validMaxOutCard=validMaxOutCard)

    rankInfo = wx_official.getRankInfo(userId)
    ebus.publishEvent(SegmentTableWinloseEvent(DIZHU_GAMEID, userId, roomId, tableId, winloseObj, rankInfo=rankInfo))
    # 处理牌桌奖励
    segmentInfo = SegmentMatchHelper.getUserSegmentInfo(userId, SegmentMatchHelper.getCurrentIssue())

    # 处理打出高倍公众号消息
    if winDoubles >= 64:
        hallBus.publishEvent(OfficialMessageEvent(DIZHU_GAMEID, userId, dizhuconf.MULTI))

    # 处理保段
    recoverConsume = None
    recoverInfo = SegmentMatchHelper.getUserSegmentRecoverData(userId)
    segmentRecoverConf = getSegmentConf().segmentRecover
    if recoverInfo.active:
        if _isRecoverForShare(userId):
            recoverConsume = {
                'type': 'share'
            }
        else:

            itemId = segmentRecoverConf.get('buy', {}).get('itemId')
            itemCount = segmentRecoverConf.get('buy', {}).get('itemCount', {})
            desc = segmentRecoverConf.get('buy', {}).get('desc', {})
            count = itemCount.get(str(recoverInfo.totalRecoverCount)) or itemCount.get('others', 10)
            userAssets = hallitem.itemSystem.loadUserAssets(userId)
            userItemCount = userAssets.balance(HALL_GAMEID, itemId, pktimestamp.getCurrentTimestamp()) or 0
            if userItemCount >= count:
                recoverConsume = {
                    'type': 'buy',
                    'itemId': itemId,
                    'count': count,
                    'desc': desc
                }

    # 获取连胜任务奖励
    winStreakRewards = None
    currentWinStreak = 0
    isAsync = None
    rewardId = None
    if SegmentWinStreakTaskHelper.isActive():
        _, winStreakRewards, currentWinStreak, isAsync = SegmentWinStreakTaskHelper.updateUserWinStreak(userId, isWin, punishState)

    # 处理九连胜公众号消息
    if currentWinStreak == 9:
        hallBus.publishEvent(OfficialMessageEvent(DIZHU_GAMEID, userId, dizhuconf.WINSTREAK))

    # 发送宝箱逻辑
    winStreakChestConf = TreasureChestHelper.getWinStreakConf(currentWinStreak)
    if TreasureChestHelper.isValidUser(userId) and winStreakRewards and winStreakChestConf:
        TGDizhu.getEventBus().publishEvent(TreasureChestEvent(DIZHU_GAMEID, userId, TREASURE_CHEST_TYPE_AS_WINSTREAK, None, winStreak=currentWinStreak))
    # 处理分享得奖
    elif isAsync and winStreakRewards:
        from dizhu.game import TGDizhu
        rewards = []
        for rewardInfo in winStreakRewards:
            rewards.append({'itemId': rewardInfo['itemId'], 'count': rewardInfo['count']})
            rewardId = RewardAsyncHelper.genRewardId()
            TGDizhu.getEventBus().publishEvent(UserRewardAsyncEvent(DIZHU_GAMEID, userId, REWARD_ASYNC_TYPE_AS_WINSTREAK, rewardId, rewards, winStreak=currentWinStreak))

    return {
        'tableRewards': DizhuSegmentRewardsHelper.processUserTableRewards(userId, winloseObj),
        'segmentInfo': segmentInfo,
        'recoverConsume': recoverConsume,
        'treasureChest': winStreakChestConf,
        'winStreakRewards': {
            'winStreak': currentWinStreak,
            'winStreakReward': winStreakRewards,
            'rewardId': rewardId
        }
    }


def _isRecoverForShare(userId):
    try:
        d = configure.getGameJson(DIZHU_GAMEID, 'match.segment', {}, 0)
        shareInfo = d.get('segmentRecover', {}).get('share', {})
        if not shareInfo:
            return False
        maxCount = shareInfo.get('maxCount', 0)
        userRecoverData = SegmentMatchHelper.getUserSegmentRecoverData(userId)
        shareRecoverCount = userRecoverData.shareRecoverCount
        if shareRecoverCount < maxCount:
            return True
        return False
    except Exception:
        return False
