# -*- coding:utf-8 -*-
'''
Created on 2017年2月25日

@author: zhaojiangang
'''
import json

import datetime

from dizhu.entity import dizhuconf
from dizhu.entity.dizhu_friend import FriendHelper
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper, UserSegmentDataIssue
from dizhucomm.entity import treasurebox, skillscore, gamesession
from dizhucomm.entity.events import UserTableOutCardBombEvent
from dizhucomm.servers.util.rpc.comm_table_remote import recoverUserAttr
import freetime.util.log as ftlog
from freetime.entity.msg import MsgPack
from hall.entity import datachangenotify, hallvip, hallflipcardluck, halluser, \
    hallitem
from hall.entity.hallpopwnd import makeTodoTaskLuckBuy, makeTodoTaskLessbuyChip
from hall.entity.todotask import TodoTaskGoldRain, TodotaskFlipCardNew, \
    TodoTaskHelper
from poker.entity.biz.exceptions import TYBizException
from poker.entity.dao import gamedata, userchip, sessiondata, userdata, daobase
from poker.protocol import router
from poker.protocol.rpccore import markRpcCall
from poker.util import strutil, timestamp as pktimestamp
from poker.entity.configure import gdata, configure
from dizhu.activities.toolbox import Redis, UserInfo, Tool


def _getLastTableChip(userId, isSupportBuyin):
    if isSupportBuyin:
        return gamedata.getGameAttrInt(userId, DIZHU_GAMEID, 'last_table_chip') or -1
    else:
        return -1

def _setLastTableChip(userId, isSupportBuyin, lastTableChip):
    if isSupportBuyin :
        gamedata.setGameAttr(userId, DIZHU_GAMEID, 'last_table_chip', lastTableChip)
         
def _resetLastTableChip(userId, isSupportBuyin):
    if isSupportBuyin :
        gamedata.setGameAttr(userId, DIZHU_GAMEID, 'last_table_chip', -1)

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def doInitTablePlayerDatas(userId, roomId, **kwargs):
    gameId = DIZHU_GAMEID
    clientId = sessiondata.getClientId(userId)
    devId = sessiondata.getDeviceId(userId)
    clientIp = sessiondata.getClientIp(userId)
    
    exp, suaddress, susex, suname, sucoin, charm = userdata.getAttrs(userId, ['exp', 'address', 'sex', 'name', 'coin', 'charm'])
    sugold, slevel, swinrate, winchips, starid, winstreak, lastwinstreak, maxwinstreak, winrate2, firstWin = gamedata.getGameAttrs(userId, gameId, ['gold', 'level', 'winrate', 'winchips', 'starid', 'winstreak', 'lastwinstreak', 'maxwinstreak', 'winrate2', 'firstWin'])

    swinrate = strutil.loads(swinrate, ignoreException=True, execptionValue={'pt':0, 'wt':0})
    winrate2 = strutil.loads(winrate2, ignoreException=True, execptionValue={'pt':0, 'wt':0})
    firstWin = strutil.loads(firstWin, ignoreException=True, execptionValue={})
    suchip = userchip.getChip(userId)
    bigRoomId = strutil.getBigRoomIdFromInstanceRoomId(roomId)
    mixConfRoomId = kwargs.get('mixConf', {}).get('roomId')
    tbplaytimes, tbplaycount = treasurebox.getTreasureBoxState(gameId, userId, mixConfRoomId or bigRoomId)
    try:
        supic, isBeauty = halluser.getUserHeadUrl(userId, clientId)
    except:
        supic, isBeauty = '', False 
    slevel = recoverUserAttr(slevel, int, 0)
    
    datas = {}
    datas['uid'] = userId
    datas['clientId'] = clientId
    datas['devId'] = recoverUserAttr(devId, str, '')
    datas['clientIp'] = recoverUserAttr(clientIp, str, '')
    datas['address'] = recoverUserAttr(suaddress, unicode, '')
    datas['sex'] = recoverUserAttr(susex, int, 0)
    datas['name'] = recoverUserAttr(suname, unicode, '')
    datas['coin'] = recoverUserAttr(sucoin, int, 0)
    datas['headUrl'] = ''
    datas['purl'] = supic
    datas['isBeauty'] = isBeauty
    datas['chip'] = suchip
    datas['exp'] = recoverUserAttr(exp, int, 0)
    datas['gold'] = recoverUserAttr(sugold, int, 0)
    datas['vipzuan'] = []
    datas['tbc'] = tbplaycount
    datas['tbt'] = tbplaytimes
    datas['level'] = slevel
    datas['wins'] = swinrate.get('wt', 0)
    datas['plays'] = swinrate.get('pt', 0)
    datas['winchips'] = recoverUserAttr(winchips, int, 0)
    datas['nextexp'] = 0
    datas['title'] = ''
    datas['medals'] = []
    datas['skillScoreInfo'] = skillscore.buildUserSkillScoreInfo(skillscore.getUserSkillScore(gameId, userId))
    datas['charm'] = 0 if charm == None else recoverUserAttr(charm, int, 0)
    datas['vipInfo'] = hallvip.userVipSystem.getVipInfo(userId)
    datas['starid'] = 0 if starid == None else recoverUserAttr(starid, int, 0)
    datas['winstreak'] = 0 if winstreak == None else recoverUserAttr(winstreak, int, 0)
    datas['lastwinstreak'] = 0 if lastwinstreak == None else recoverUserAttr(lastwinstreak, int, 0)
    datas['maxwinstreak'] = 0 if maxwinstreak == None else recoverUserAttr(maxwinstreak, int, 0)
    datas['gameClientVer'] = gamesession.getGameClientVer(gameId, userId)
    datas['winrate2'] = winrate2
    datas['firstWin'] = firstWin

    # TODO 查询用户增值位
    datas['wearedItems'] = []
    userBag = hallitem.itemSystem.loadUserAssets(userId).getUserBag()
    timestamp = pktimestamp.getCurrentTimestamp()
    memberCardItem = userBag.getItemByKindId(hallitem.ITEM_MEMBER_NEW_KIND_ID)
    datas['memberExpires'] = memberCardItem.expiresTime if memberCardItem else 0
    datas['registerDays'] = UserInfo.getRegisterDays(userId, timestamp)
    item = userBag.getItemByKindId(hallitem.ITEM_CARD_NOTE_KIND_ID)

    # 新用户的计次记牌器
    newUserReward = configure.getGameJson(gameId, 'login.reward', {}).get('newUserReward')
    if newUserReward:
        if newUserReward.get('open', 0):
            cardNoteCount = newUserReward.get('cardNoteCount', 0)
            if cardNoteCount:
                pt = swinrate.get('pt', 0)
                if cardNoteCount - pt >= 1:
                    datas['cardNotCount'] = max(1, cardNoteCount - pt)

    if item and not item.isDied(timestamp):
        datas['cardNotCount'] = max(1, item.balance(timestamp))
    
    if ftlog.is_debug():
        ftlog.debug('table_remote.doInitTablePlayerDatas',
                    'userId=', userId,
                    'clientId=', clientId,
                    'datas=', datas)
    return datas

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def buyin(userId, roomId, clientId, tableId, buyinChip, minCoin, continueBuyin):
    minchip = min(minCoin, buyinChip)
    maxchip = max(minCoin, buyinChip)
    tfinal, final, delta = userchip.setTableChipToRange(userId,
                                                        DIZHU_GAMEID,
                                                        minchip,
                                                        maxchip,
                                                        'TABLE_SITDOWN_SET_TCHIP',
                                                        roomId,
                                                        clientId,
                                                        tableId)
    datachangenotify.sendDataChangeNotify(DIZHU_GAMEID, userId, 'udata')
    ftlog.info('new_table_remote.buyin',
               'userId=', userId,
               'roomId=', roomId,
               'clientId=', clientId,
               'tableId=', tableId,
               'buyinChip=', buyinChip,
               'minCoin=', minCoin,
               'continueBuyin=', continueBuyin,
               'tfinal=', tfinal,
               'final=', final,
               'delta=', delta)
    return tfinal, final, delta

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def cashin(userId, roomId, clientId, tableId, cashinChip):
    tfinal, final, delta = userchip.moveAllTableChipToChip(userId,
                                                           DIZHU_GAMEID,
                                                           'TABLE_STANDUP_TCHIP_TO_CHIP',
                                                           roomId,
                                                           clientId,
                                                           tableId)
    userchip.delTableChips(userId, [tableId])
    if ftlog.is_debug():
        ftlog.debug('new_table_remote.cashin',
                    'userId=', userId,
                    'roomId=', roomId,
                    'clientId=', clientId,
                    'cashinTableId=', tableId,
                    'cashinChip=', cashinChip,
                    'tfinal=', tfinal,
                    'final=', final,
                    'delta=', delta)
    datachangenotify.sendDataChangeNotify(DIZHU_GAMEID, userId, 'udata')
    return final

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendWinStreakReward(userId, roomId, clientId, tableId, assetKindId, count):
    try:
        userAssets = hallitem.itemSystem.loadUserAssets(userId)
        _, addCount, final = userAssets.addAsset(DIZHU_GAMEID, assetKindId, count, pktimestamp.getCurrentTimestamp(), 'DDZ_WINSTREAK_REWARD', roomId)
        return addCount, final
    except:
        ftlog.error('new_table_remote.sendWinStreakReward gameId=', DIZHU_GAMEID,
                    'userId=', userId,
                    'assetKindId=', assetKindId,
                    'count=', count)
        return 0, 0

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def publishUserTableBomb(userId, roomId, tableId, userIds, **kwargs):
    try:
        mixRoomId = kwargs.get('mixRoomId')
        roomName = kwargs.get('roomName', '')
        from dizhu.game import TGDizhu
        TGDizhu.getEventBus().publishEvent(UserTableOutCardBombEvent(DIZHU_GAMEID, userId, roomId, tableId, userIds, mixConfRoomId=mixRoomId, roomName=roomName))
    except:
        ftlog.error('new_table_remote.publishUserTableBomb gameId=', DIZHU_GAMEID,
                    'userId=', userId,
                    'roomId=', roomId,
                    'tableId=', tableId,
                    'mixRoomId=', kwargs.get('mixRoomId'))


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def getRoomMaxWinStreak(userId, roomId):
    try:
        bigRoomId = strutil.getBigRoomIdFromInstanceRoomId(roomId)
        ret = daobase.executeUserCmd(userId, 'HGET', 'maxWinStreak' + ':' + str(DIZHU_GAMEID) + ':' + str(userId),str(bigRoomId))
        return strutil.loads(ret) if ret else None

    except:
        ftlog.error('new_table_remote.getRoomMaxWinStreak gameId=', DIZHU_GAMEID,
                    'userId=', userId)
        return


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendRoomMaxWinStreak(userId, roomId, maxWinStreak):
    try:
        bigRoomId = strutil.getBigRoomIdFromInstanceRoomId(roomId)
        d = {
            'maxWinStreak': maxWinStreak
        }
        return daobase.executeUserCmd(userId, 'HSET', 'maxWinStreak' + ':' + str(DIZHU_GAMEID) + ':' + str(userId),str(bigRoomId), strutil.dumps(d))

    except:
        ftlog.error('new_table_remote.sendRoomMaxWinStreak gameId=', DIZHU_GAMEID,
                    'userId=', userId)
        return None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def getUserDailyPlayTimes(userId, roomId):
    try:
        bigRoomId = strutil.getBigRoomIdFromInstanceRoomId(roomId)
        ret = daobase.executeUserCmd(userId, 'HGET', 'dailyplaytimes' + ':' + str(DIZHU_GAMEID) + ':' + str(userId), str(bigRoomId))
        return strutil.loads(ret) if ret else None
        
    except:
        ftlog.error('new_table_remote.sendDailyPlayTimes gameId=', DIZHU_GAMEID,
                    'userId=', userId)
        return 


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendUserDailyPlayTimes(userId, roomId, timestamp, dailyplaytimes):
    try:
        bigRoomId = strutil.getBigRoomIdFromInstanceRoomId(roomId)
        d = {
            'timestamp': timestamp,
            'dailyplaytimes': dailyplaytimes
        }
        return daobase.executeUserCmd(userId, 'HSET', 'dailyplaytimes' + ':' + str(DIZHU_GAMEID) + ':' + str(userId), str(bigRoomId), strutil.dumps(d))
        
    except:
        ftlog.error('new_table_remote.sendUserDailyPlayTimes gameId=', DIZHU_GAMEID,
                    'userId=', userId)
        return None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def setHonorCardDailyPlayTimes(userId, todayDate, count):
    try:
        d = {'date': todayDate, 'count': count}
        return daobase.executeUserCmd(userId, 'HSET', 'honorPlayTimes' + ':' + str(DIZHU_GAMEID) + ':' + str(userId), 'dailyPlayTimes', strutil.dumps(d))
    except:
        ftlog.error('new_table_remote.setHonorCardDailyPlayTimes gameId=', DIZHU_GAMEID, 'userId=', userId)
        return None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def getHonorCardDailyPlayTimes(userId, todayDate):
    try:
        ret = daobase.executeUserCmd(userId, 'HGET', 'honorPlayTimes' + ':' + str(DIZHU_GAMEID) + ':' + str(userId), 'dailyPlayTimes')
        jstr = strutil.loads(ret) if ret else None
        if jstr:
            date = jstr.get('date', 0)
            return 0 if todayDate > date else jstr.get('count', 0)
        return 0
    except:
        ftlog.error('new_table_remote.getHonorCardDailyPlayTimes gameId=', DIZHU_GAMEID, 'userId=', userId)
        return None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def setUserGiftBuff(userId, buffType, timestamp):
    try:
        isEjected = pktimestamp.getDayStartTimestamp()
        d= {'expiretime': timestamp, 'ejected': isEjected}
        return daobase.executeUserCmd(userId, 'HSET', 'GiftBuff' + ':' + str(DIZHU_GAMEID) + ':' + str(userId),
                                      str(buffType), strutil.dumps(d))
    except:
        ftlog.error('new_table_remote.setUserWinStreakGiftBuff gameId=', DIZHU_GAMEID, 'userId=', userId)
        return None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def getUserGiftBuff(userId, buffType):
    try:
        ret = daobase.executeUserCmd(userId, 'HGET', 'GiftBuff' + ':' + str(DIZHU_GAMEID) + ':' + str(userId),
                                      str(buffType))
        if ret:
            jstr = strutil.loads(ret)
            return jstr.get('expiretime'), jstr.get('ejected') == pktimestamp.getDayStartTimestamp()
        return  None, None
    except:
        ftlog.error('new_table_remote.setUserWinStreakGiftBuff gameId=', DIZHU_GAMEID, 'userId=', userId)
        return None, None

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendGiftBuffReward(userId, roomId, assetKindId, count, eventId):
    try:
        userAssets = hallitem.itemSystem.loadUserAssets(userId)
        _, addCount, final = userAssets.addAsset(DIZHU_GAMEID, assetKindId, count, pktimestamp.getCurrentTimestamp(),
                                                 str(eventId), roomId)
        return addCount, final
    except:
        ftlog.error('new_table_remote.sendWinStreakReward gameId=', DIZHU_GAMEID, 'userId=', userId, 'assetKindId=',
                    assetKindId, 'count=', count)
        return 0, 0

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendDailyPlayTimesWinReward(userId, roomId, clientId, tableId, assetKindId, count):
    try:
        userAssets = hallitem.itemSystem.loadUserAssets(userId)
        _, addCount, final = userAssets.addAsset(DIZHU_GAMEID, assetKindId, count, pktimestamp.getCurrentTimestamp(), 'DDZ_GAMEWIN_REWARD', roomId)
        return addCount, final
    except:
        ftlog.error('new_table_remote.sendDailyPlayTimesWinReward gameId=', DIZHU_GAMEID,
                    'userId=', userId,
                    'assetKindId=', assetKindId,
                    'count=', count)
        return 0, 0

def processLoseOutRoom(gameId, userId, clientId, roomId):
    # 处理江湖救急流程
    if ftlog.is_debug():
        ftlog.debug('new_table_remote.processLoseOutRoom gameId=', gameId,
                    'userId=', userId,
                    'clientId=', clientId,
                    'roomId=', roomId)
    title = ''
    desc = ''
    tips = ''
    vipBenefits = 0
    try:
        consumeCount, _finalCount, vipBenefits = hallvip.userVipSystem.gainAssistance(gameId, userId)
        if ftlog.is_debug():
            ftlog.debug('new_table_remote.processLoseOutRoom gameId=', gameId,
                        'userId=', userId,
                        'roomId=', roomId,
                        'consumeCount=', consumeCount,
                        'vipBenefits=', vipBenefits)
        if consumeCount > 0:
            title = hallflipcardluck.getString('vipBenefits.title', 'VIP专属江湖救急')
            desc = hallflipcardluck.getString('vipBenefits.desc', '金币不够啦，送您一次翻奖机会，快来试试手气吧')
            tips = hallflipcardluck.getString('vipBenefits.title', '再送您${vipBenefits}江湖救急')
            tips = strutil.replaceParams(tips, {'vipBenefits':str(vipBenefits)})
    except TYBizException:
        pass
    except:
        ftlog.error('new_table_remote.processLoseOutRoom gameId=', gameId,
                    'userId=', userId,
                    'roomId=', roomId)
    todotasks = []
    if vipBenefits > 0:
        goldRainDesc = strutil.replaceParams(hallvip.vipSystem.getGotGiftDesc(), {'content':'%s金币' % (vipBenefits)})
        todotasks.append(TodoTaskGoldRain(goldRainDesc))
        datachangenotify.sendDataChangeNotify(gameId, userId, 'chip')
    else:
        desc = hallflipcardluck.getString('benefits.desc', '金币不够啦，送您一次翻奖机会，快来试试手气吧')
        if ftlog.is_debug():
            ftlog.debug('new_table_remote.processLoseOutRoom gameId=', gameId,
                        'userId=', userId,
                        'roomId=', roomId,
                        'benefits=', desc)
    todotasks.append(TodotaskFlipCardNew(gameId, roomId, title, desc, tips))
    return TodoTaskHelper.sendTodoTask(gameId, userId, todotasks)


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def sendUserBenefitsIfNeed(gameId, userId, roomId):
    # vip奖励映射表
    vipmap = dizhuconf.getPublic().get('VipBenefits', {}).get('VipMap', {})
    # 玩家vip等级
    userChip = userchip.getChip(userId)
    info = hallvip.userVipSystem.getUserVip(userId)
    uservip = info.vipLevel.level if info else 0
    vipmapitem = vipmap.get(str(uservip))
    sendMinCoin = dizhuconf.getPublic().get('VipBenefits', {}).get('SendMinCoin', 0)
    if ftlog.is_debug():
        ftlog.debug('sendUserBenefitsIfNeed: vipmapitem',
                    'userId=', userId,
                    'userChip=', userChip,
                    'sendMinCoin=', sendMinCoin,
                    'vipmapitem=', vipmapitem)
    if not vipmapitem:
        return
    chip = vipmapitem.get('chip')
    sendCount = vipmapitem.get('sendCount')
    minRoomLevel = vipmapitem.get('minRoomLevel')
    if chip <= 0 or sendCount <= 0 or minRoomLevel <= 0 or userChip >= sendMinCoin:
        return

    # 发送VIP救济金
    ret = sendUserVipBenefits(userId, roomId, minRoomLevel, sendCount, chip)
    if not ret:
        return
    vipmsg = [
        [{'type':'ttf', 'font':'ArialMT', 'text':'VIP' + str(uservip), 'color':0x482904},
         {'type':'ttf', 'font':'ArialMT', 'text':'特权，附', 'color':0x482904},
         {'type':'ttf', 'font':'ArialMT', 'text':'+' + str(chip), 'color':0xFF0000},
         {'type':'ttf', 'font':'ArialMT', 'text':'金！', 'color':0x482904}]
    ]

    if ftlog.is_debug():
        ftlog.debug('sendUserBenefitsIfNeed:',
                    'userId=', userId,
                    'uservip=', uservip)

    mo = MsgPack()
    mo.setCmd('table_call')
    mo.setResult('gameId', gameId)
    mo.setResult('userId', userId)
    mo.setResult('action', 'benefits')
    mo.setResult('benefits', 1)
    mo.setResult('message', json.dumps(vipmsg))
    router.sendToUser(mo, userId)


@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def addWechatFriend(userId, userIds):
    FriendHelper.addFriend(userId, userIds)


def sendUserVipBenefits(userId, roomId, minRoomLevel, sendCount, chip):
    if minRoomLevel < 1 or sendCount <= 0:
        return False

    bigroomId = gdata.getBigRoomId(roomId)
    roomconf = gdata.getRoomConfigure(bigroomId)
    if not roomconf:
        return False
    roomlevel = roomconf.get('roomLevel', 1)
    if roomlevel < minRoomLevel:
        if ftlog.is_debug():
            ftlog.debug('sendUserVipBenefits: roomlevel',
                        'userId=', userId,
                        'roomlevel=', roomlevel,
                        'minRoomLevel=', minRoomLevel)
        return False

    rediskey = 'vip.benefits'
    data = Redis.readJson(userId, rediskey)
    timestamp = data.get('timestamp', 0)
    counter = data.get('counter', 0)

    now = datetime.datetime.now()
    last = datetime.datetime.fromtimestamp(timestamp)
    if last.year != now.year or last.month != now.month or last.day != now.day:
        counter = 0

    if counter >= sendCount:
        if ftlog.is_debug():
            ftlog.debug('sendUserVipBenefits: sendCount',
                'userId=', userId,
                'sendCount=', sendCount,
                'counter=', counter)
        return False

    data['counter'] = counter + 1
    data['timestamp'] = Tool.datetimeToTimestamp(now)

    Redis.writeJson(userId, rediskey, data)
    UserInfo.incrChip(userId, 6, chip, 'BENEFITS_VIP_SEND')
    if ftlog.is_debug():
        ftlog.debug('sendUserVipBenefits:',
                    'userId=', userId,
                    'counter=', data['counter'],
                    'chip=', chip)
    return True


def processLoseRoundOver(gameId, userId, clientId, roomId, **kwargs):
    # 踢出房间的幸运大礼包
    minCoin = kwargs.get('minCoin', 0)
    luckBuyOrLessBuyChip = makeTodoTaskLuckBuy(gameId, userId, clientId, roomId)
    if not luckBuyOrLessBuyChip:
        luckBuyOrLessBuyChip = makeTodoTaskLessbuyChip(gameId, userId, clientId, roomId, minCoin=minCoin)

    if not luckBuyOrLessBuyChip:
        return
    todotasks = [luckBuyOrLessBuyChip]
    return TodoTaskHelper.sendTodoTask(gameId, userId, todotasks)


@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def doGetUserSegment(userId, **kwargs):
    userSegmentData = SegmentMatchHelper.getUserSegmentDataIssue(userId, SegmentMatchHelper.getCurrentIssue()) or UserSegmentDataIssue()
    return userSegmentData.segment, userSegmentData.currentStar

@markRpcCall(groupName='userId', lockName='userId', syncCall=1)
def doGetUserDailyPlayCount(userId, gameId, **kwargs):
    dailyPlay = gamedata.getGameAttrs(userId, gameId, ['dailyPlay'])
    dailyPlay = strutil.loads(dailyPlay[0], ignoreException=True, execptionValue={'count': 0, 'timestamp': pktimestamp.getCurrentTimestamp()})
    if ftlog.is_debug():
        ftlog.debug('doGetUserDailyPlayCount userId=', userId,
                    'dailyPlay=', dailyPlay)
    return dailyPlay['count']


def doGetUserDailyPlayCountLocal(userId, gameId, **kwargs):
    dailyPlay = gamedata.getGameAttrs(userId, gameId, ['dailyPlay'])
    dailyPlay = strutil.loads(dailyPlay[0], ignoreException=True, execptionValue={'count': 0, 'timestamp': pktimestamp.getCurrentTimestamp()})
    if ftlog.is_debug():
        ftlog.debug('doGetUserDailyPlayCount userId=', userId,
                    'dailyPlay=', dailyPlay)
    return dailyPlay['count']
