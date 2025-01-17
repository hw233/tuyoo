# -*- coding: utf-8 -*-
'''
Created on 2015年5月20日

@author: zqh
'''
import functools
import random
import time

from dizhu.entity import dizhuconf, skillscore, dizhutask, dizhu_login_reward
from dizhu.entity.dizhuconf import DIZHU_GAMEID
import freetime.util.log as ftlog
from dizhu.entity.segment.dao import segmentdata
from freetime.core.timer import FTTimer
from hall.entity import halluser
from hall.entity.user_analysis import analysis_api
from poker.entity.dao import gamedata, userdata, userchip
import poker.util.timestamp as pktimestamp
from poker.util import strutil


def getInitDataKeys():
    return dizhuconf.getGameDataKeys()


def getInitDataValues():
    return dizhuconf.getGameDataValues()


def getGameUserNextExp(level):
    expdat = dizhuconf.getExpDataLevel()
    if level == None :
        level = 0
    else:
        level = abs(int(level))
    if level < len(expdat) :
        nextexp = expdat[level]
    else:
        nextexp = expdat[-1]
    return nextexp


def getGameUserTitle(level):
    title = dizhuconf.getExpDataTitle()
    if level == None or level <= 0:
        return title[0]
    
    level = abs(int(level))
    n = abs((level - 1) / 3)
    if n < len(title):
        utitle = title[n]
    else:
        utitle = title[-1]
    return utitle


def getExpLevel(cexp):
    expdat = dizhuconf.getExpDataLevel()
    if cexp <= expdat[0]:
        return 0
    else:
        for x in xrange(len(expdat) - 1):
            if cexp <= expdat[x + 1] and cexp > expdat[x]:
                return x + 1
    return len(expdat)


def getReferrer(userId):
    referrer = gamedata.getGameAttrInt(userId, DIZHU_GAMEID, 'referrer')
    return referrer


def getCanSetReferrer(userId):
    if halluser.getRegisterDay(userId) >= 3:
        return False
    referrer = getReferrer(userId)
    return 0 == referrer


def getGameInfo(userId, clientId):
    ftlog.debug('dizhu.getGameInfo->', userId, clientId)

    ukeys = getInitDataKeys()
    uvals = gamedata.getGameAttrs(userId, DIZHU_GAMEID, ukeys)
    uvals = list(uvals)
    values = getInitDataValues()
    for x in xrange(len(uvals)):
        if uvals[x] == None:
            uvals[x] = values[x]
    gdata = dict(zip(ukeys, uvals))

    level = gdata['level']
    gdata['nextexp'] = getGameUserNextExp(level)
    gdata['title'] = getGameUserTitle(level)
    gdata['referrerSwitch'] = dizhuconf.getReferrerSwitch()
    gdata['canSetReferrer'] = getCanSetReferrer(userId)
    gdata['skillScoreInfo'] = skillscore.score_info(userId)
    gdata['charm'] = userdata.getCharm(userId)
    gdata['chip'] = userchip.getUserChipAll(userId)
    gdata['dashifen'] = getDaShiFen(userId, clientId)
    ftlog.debug('dizhu.getGameInfo->', userId, clientId, gdata)
    return gdata


def getDaShiFen(userId, clientId):
    ftlog.debug('dizhu.getDaShiFen->', userId, clientId)
    return skillscore.score_info(userId)


def createGameData(userId, clientId):
    '''
    初始化该游戏的所有的相关游戏数据
    包括: 主游戏数据gamedata, 道具item, 勋章medal等
    返回主数据的键值和值列表
    '''
    ftlog.debug('dizhu.createGameData->', userId, clientId)
    gdkeys = getInitDataKeys()
    gvals = getInitDataValues()
    gamedata.setGameAttrs(userId, DIZHU_GAMEID, gdkeys, gvals)
    return gdkeys, gvals


def loginGame(userId, gameId, clientId, iscreate, isdayfirst):
    '''
    用户登录一个游戏, 游戏自己做一些其他的业务或数据处理
    例如: 1. IOS大厅不发启动资金的补丁, 
         2. 麻将的记录首次登录时间
         3. 游戏插件道具合并至大厅道具
    '''
    ftlog.debug('dizhu.loginGame->', userId, gameId, clientId, iscreate, isdayfirst)
    dizhutask._onUserLogin(gameId, userId, clientId, iscreate, isdayfirst)
    # if not (iscreate or hallstartchip.needSendStartChip(userId, gameId)):
    #     hallbenefits.benefitsSystem.sendBenefits(gameId, userId, pktimestamp.getCurrentTimestamp())
    if iscreate:
        dizhu_login_reward.sendLoginReward(gameId, userId, clientId, iscreate, isdayfirst)
    FTTimer(0, functools.partial(processUserBehavior, userId))


def processUserBehavior(userId):
    # 进一步优化，存储过期时间，每2小时刷一次
    shareBehaviorFeatureTimestamp = segmentdata.getSegmentAttr(userId, DIZHU_GAMEID, 'shareBehaviorFeatureTimestamp')
    if not shareBehaviorFeatureTimestamp:
        shareBehaviorFeatureTimestamp = pktimestamp.getCurrentTimestamp()
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, 'shareBehaviorFeatureTimestamp', shareBehaviorFeatureTimestamp)

    if pktimestamp.getCurrentTimestamp() - shareBehaviorFeatureTimestamp > 3600 * 2 + random.randint(0, 300):
        segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, 'shareBehaviorFeatureTimestamp', pktimestamp.getCurrentTimestamp())
        # 存储用户行为特征库数据
        params = {
            'user_id': userId,
            'cloud_id': 29,
            'game_id': 6,
            'time': int(time.time())
        }
        ec, datas = analysis_api.requestAnalysis('api.getUserFeature', params)
        if ftlog.is_debug():
            ftlog.debug('dizhuaccount.loginGame setUserBehaviourFeature',
                        'userId=', userId,
                        'ec=', ec,
                        'datas=', datas)
        share_behavior = datas.get('sharing_behavior', None) if ec == 1 else None
        if share_behavior:
            segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, 'shareBehaviorFeature', share_behavior)

        noInvitedDiamond = datas.get('no_invited_get_diamond', None) if ec == 1 else None
        if noInvitedDiamond:
            segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, 'noInvitedGetDiamond', noInvitedDiamond)

        roundsShareTimes = datas.get('rounds_share_times', None) if ec == 1 else None
        if roundsShareTimes:
            segmentdata.setSegmentAttr(userId, DIZHU_GAMEID, 'roundsShareTimes', roundsShareTimes)


def getUserGamePlayTimes(userId):
    '''
    获取用户当游戏总局数
    '''
    winrate = gamedata.getGameAttrs(userId, 6, ['winrate'])
    winrate = strutil.loads(winrate[0], ignoreException=True, execptionValue={'pt': 0, 'wt': 0})
    return winrate.get('pt', 0)
