# -*- coding=utf-8 -*-
'''
Created on 2018年6月1日
@author: wangyonghui
'''

import json
import freetime.util.log as ftlog
from dizhu.entity import dizhu_util
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.segment.user_share_behavior import isInterventionUser
from hall.entity.hallusercond import UserConditionRegister
from hall.entity.usercoupon import user_coupon_details
from hall.entity.usercoupon.events import UserCouponReceiveEvent
from hall.game import TGHall
from poker.entity.biz.content import TYContentItem
from poker.entity.configure import configure
from poker.entity.dao import userdata, gamedata
import poker.util.timestamp as pktimestamp

REWARD_STATE_IDEAL = 0  # 空闲态
REWARD_STATE_RECEIVED = 1  # 已领取

MAX_HELP_COUNT = 2


class Invitation(object):
    def __init__(self, userId):
        self.userId = userId
        self.rewardState = REWARD_STATE_IDEAL

    def fromDict(self, d):
        self.rewardState = d.get('rewardState')
        return self

    def toDict(self):
        return {
            'userId': self.userId,
            'rewardState': self.rewardState
        }


class SimpleInviteStatus(object):
    '''
    简单邀请关系，添加有效期，有效期1天
    '''
    def __init__(self, userId):
        self.userId = userId
        self.timestamp = pktimestamp.getCurrentTimestamp()
        self.inviteeRewardList = []  # 被邀请者列表，存 Invitation 对象
        self.inviterUserIdList = []  # 帮助的邀请者列表， 存 userId
        self.bigRewardState = REWARD_STATE_IDEAL

    def fromDict(self, d):
        '''
        从数据恢复邀请状态
        '''
        timestamp = d.get('timestamp', 0)
        if not pktimestamp.is_same_day(timestamp, pktimestamp.getCurrentTimestamp()):
            return self

        self.timestamp = timestamp
        self.inviterUserIdList = d.get('inviterUserIdList', [])

        self.inviteeRewardList = []
        inviteeRewardList = d.get('inviteeRewardList', [])
        for inviteeReward in inviteeRewardList:
            invitation = Invitation(inviteeReward['userId']).fromDict(inviteeReward)
            self.inviteeRewardList.append(invitation)

        self.bigRewardState = d.get('bigRewardState', REWARD_STATE_IDEAL)
        return self

    def toDict(self):
        '''
        编码保存
        '''
        return {
            'timestamp': self.timestamp,
            'inviterUserIdList': self.inviterUserIdList,
            'bigRewardState': self.bigRewardState,
            'inviteeRewardList': [inviteeReward.toDict() for inviteeReward in self.inviteeRewardList]
        }

    def addInviterUserIdList(self, inviterUserId, pointId):
        if inviterUserId in self.inviterUserIdList:
            return 1, '您已帮助过此用户'
        if inviterUserId == self.userId:
            return 2, '您不能帮助自己'

        if len(self.inviterUserIdList) >= MAX_HELP_COUNT:
            return 3, '您今日帮助次数剩余为（%s/%s）' % (MAX_HELP_COUNT, MAX_HELP_COUNT)

        status = loadStatus(inviterUserId)
        if len(status.inviteeRewardList) >= len(getSimpleInviteRewardsConf()):
            return 4, '您帮助的用户已领取所有奖励'

        if pointId not in getSimpleInvitePoinIdList():
            return 5, '此条分享链接不支持签到奖励哟'

        # 可以帮助了
        self.inviterUserIdList.append(inviterUserId)
        # 被帮助者
        status.inviteeRewardList.append(Invitation(self.userId))
        saveStatus(status)
        saveStatus(self)
        nickName, url =  getUserNameAndPic(inviterUserId)
        reward = None
        for index, invitation in enumerate(status.inviteeRewardList):
            if invitation.userId == self.userId:
                reward = getSimpleInviteRewardByIndex(index)
        return 0, '感谢您的帮助\n玩家 %s 成功获得 %s \n 今日剩余帮助次数(%s/%s)' % (nickName, reward['desc'],
                                                         MAX_HELP_COUNT - len(self.inviterUserIdList), MAX_HELP_COUNT)


def loadStatus(userId):
    '''
    加载用户推广状态
    '''
    status = None
    dStr = None
    try:
        dStr = gamedata.getGameAttr(userId, DIZHU_GAMEID, 'simple_invite')
        if ftlog.is_debug():
            ftlog.debug('dizhu_invite.loadStatus userId=', userId,
                        'dStr=', dStr)
        if dStr:
            d = json.loads(dStr)
            status = SimpleInviteStatus(userId).fromDict(d)
    except:
        ftlog.error('dizhu_invite.loadStatus userId=', userId, 'dStr=', dStr)

    if not status:
        status = SimpleInviteStatus(userId)
    return status


def saveStatus(status):
    '''
    保存数据
    '''
    d = status.toDict()
    jstr = json.dumps(d)
    gamedata.setGameAttr(status.userId, DIZHU_GAMEID, 'simple_invite', jstr)
    if ftlog.is_debug():
        ftlog.debug('dizhu_invite.loadStatus userId=', status.userId,
                    'status=', status.toDict())


def getUserNameAndPic(userId):
    name, pic = userdata.getAttrs(userId, ['name', 'purl'])
    if not name or name == '':
        name = str(userId)
    if not pic:
        pic = ''
    return name, pic


# ---------------------------------------
# 配置相关，获取签到奖励以及完成所有签到的终极奖励
# ---------------------------------------

def getSimpleInviteConf():
    return configure.getGameJson(6, 'dizhu_invite', {})


def getSimpleInviteRewardsConf():
    '''
    获取简单邀请的奖励配置
    '''
    conf = getSimpleInviteConf()
    return conf.get('inviteRewardsByIndex', [])


def getSimpleInviteRewardByIndex(index):
    '''
    获取简单邀请的奖励配置
    '''
    simpleInviteRewardsConf = getSimpleInviteRewardsConf()
    if not simpleInviteRewardsConf:
        return None

    if index >= len(simpleInviteRewardsConf) or index < 0:
        return None
    return simpleInviteRewardsConf[index]


def getSimpleInviteBigReward(userId):
    '''
    获取大奖
    '''
    conf = getSimpleInviteConf()

    if conf.get('switch'):
        conditon = conf.get('condition')
        cond = UserConditionRegister.decodeFromDict(conditon)
        retCheck = cond.check(DIZHU_GAMEID, userId, None, None)
        ftlog.debug('dizhu_invite.getSimpleInviteBigReward userId=', userId,
                    'retCheck=', retCheck,
                    'isInterventionUser=', isInterventionUser(userId))
        if retCheck:
            firstBigRewards = gamedata.getGameAttr(userId, DIZHU_GAMEID, 'firstBigRewards')
            if not firstBigRewards:
                return conf.get('firstBigRewards') if conf.get('firstBigRewards') else {}
        if isInterventionUser(userId):
            return conf.get('interventionBigRewards') if conf.get('interventionBigRewards') else {}

    return dizhu_util.getItemByWeight(conf.get('bigRewards')) if conf.get('bigRewards') else {}


def getSimpleInvitePoinIdList():
    '''
    获取poinIdList
    '''
    conf = getSimpleInviteConf()
    return conf.get('pointIdList', [])


class InviteHelper(object):
    @classmethod
    def getInviteeList(cls, userId):
        ret = []
        status = loadStatus(userId)
        inviteeRewardList = status.inviteeRewardList
        for index, rewardConf in enumerate(getSimpleInviteRewardsConf()):
            try:
                tempDict = {}
                tempDict['itemId'] = rewardConf['itemId']
                tempDict['count'] = rewardConf['count']
                tempDict['desc'] = rewardConf['desc']
                tempDict['userId'] = inviteeRewardList[index].userId
                nickName, avatar = getUserNameAndPic(inviteeRewardList[index].userId)
                tempDict['avatar'] = avatar
                tempDict['nickName'] = nickName
                tempDict['rewardState'] = inviteeRewardList[index].rewardState
                ret.append(tempDict)

            except Exception:
                ret.append(rewardConf)

        bigReward = {}
        bigRewardConf = getSimpleInviteBigReward(userId)
        if bigRewardConf:
            bigReward['itemId'] = bigRewardConf['itemId']
            bigReward['count'] = bigRewardConf['count']
            bigReward['desc'] = bigRewardConf['desc']
            bigReward['state'] = status.bigRewardState

        return ret, bigReward


    @classmethod
    def doBindInviteUser(cls, userId, inviteUserId, pointId):
        status = loadStatus(userId)
        return status.addInviterUserIdList(inviteUserId, pointId)

    @classmethod
    def doGetInviteRewardAll(cls, userId):
        status = loadStatus(userId)
        inviteeRewardList = status.inviteeRewardList
        rewardsList = []
        bigReward = None
        save = False
        for index, rewardState in enumerate(inviteeRewardList):
            if rewardState.rewardState == REWARD_STATE_IDEAL:
                rewardState.rewardState = REWARD_STATE_RECEIVED
                save = True
                r = getSimpleInviteRewardByIndex(index)
                if r:
                    rewardsList.append(r)
        if rewardsList:
            contentItems = TYContentItem.decodeList(rewardsList)
            assetList = dizhu_util.sendRewardItems(userId, contentItems, '', 'DIZHU_QIANDAO_REWARD', 0)

        if len(inviteeRewardList) >= len(getSimpleInviteRewardsConf()):
            bigReward = getSimpleInviteBigReward(userId)
            if bigReward:
                contentItems = TYContentItem.decodeList([bigReward])
                assetList = dizhu_util.sendRewardItems(userId, contentItems, '', 'DIZHU_QIANDAO_REWARD', 0)
                if bigReward.get('itemId') == 'user:coupon':
                    TGHall.getEventBus().publishEvent(UserCouponReceiveEvent(9999, userId, bigReward['count'],
                                                                         user_coupon_details.USER_COUPON_INVITE))
                status.bigRewardState = REWARD_STATE_RECEIVED
                save = True
                conf = getSimpleInviteConf()
                if conf.get('switch'):
                    gamedata.setGameAttr(userId, DIZHU_GAMEID, 'firstBigRewards', 1)
        if save:
            saveStatus(status)
        return rewardsList, bigReward



