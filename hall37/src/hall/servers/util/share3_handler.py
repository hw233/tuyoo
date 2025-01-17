# -*- coding:utf-8 -*-
'''
Created on 2018年5月7日

@author: zhaojiangang
'''
from sre_compile import isstring

from freetime.entity.msg import MsgPack
from hall.entity import hall_share3, hallitem
from hall.servers.common.base_checker import BaseMsgPackChecker
from poker.protocol import router
from poker.protocol.decorator import markCmdActionHandler, markCmdActionMethod
import poker.util.timestamp as pktimestamp
from poker.util import strutil


@markCmdActionHandler    
class Share3TcpHandler(BaseMsgPackChecker):
    def _check_param_burialId(self, msg, key, params):
        value = msg.getParam(key)
        if isstring(value):
            return None, value
        return 'ERROR of burialId !' + str(value), None
    
    def _check_param_whereToShare(self, msg, key, params):
        value = msg.getParam(key)
        if isstring(value):
            return None, value
        return 'ERROR of whereToShare !' + str(value), None
    
    def _check_param_urlParams(self, msg, key, params):
        value = msg.getParam(key, {})
        if isinstance(value, dict) :
            return None, value
        return 'ERROR of urlParams !' + str(value), None
    
    def _check_param_pointId(self, msg, key, params):
        value = msg.getParam(key)
        if isinstance(value, int):
            return None, int(value)
        return 'ERROR of pointId !' + str(value), None
    
    @classmethod
    def _doGetBurials(cls, gameId, userId, clientId):
        burials = hall_share3.getBurials(gameId, userId, clientId)
        eBurials = [{'burialId': burial['burialId'], 'tips': burial['tips']} for burial in burials]
        mp = MsgPack()
        mp.setCmd('hall_share3')
        mp.setResult('action', 'get_burials')
        mp.setResult('gameId', gameId)
        mp.setResult('userId', userId)
        mp.setResult('burials', eBurials)
        return mp

    @markCmdActionMethod(cmd='hall_share3', action='get_burials', clientIdVer=0)
    def doGetBurials(self, gameId, userId, clientId):
        mp = self._doGetBurials(gameId, userId, clientId)
        if mp:
            router.sendToUser(mp, userId)
    
    @classmethod
    def buildShare(cls, gameId, userId, clientId, sharePoint, urlParams):
        items = sharePoint.reward.content.getItems() if sharePoint.reward else []
        content = hall_share3.getShareContent(userId, clientId, sharePoint, gameId) or {}
        rewardCount, totalRewardCount = hall_share3.getRewardCount(gameId, userId, sharePoint, pktimestamp.getCurrentTimestamp())
        shareGroupAll = True
        return {
            'pointId': sharePoint.pointId,
            'whereToReward': sharePoint.whereToReward,
            'shareGroupAll': shareGroupAll,
            'shareId': content.get('shareId', 0),
            'title': strutil.replaceParams(content.get('title', ''), urlParams),
            'pic': content.get('pic', ''),
            'flagId': content.get('flagId', 0),
            'remRewardCount': totalRewardCount - rewardCount,
            'totalRewardCount': totalRewardCount,
            'rewards': hallitem.buildItemInfoList(items)
        }
    
    @classmethod
    def _doGetBurialShare(cls, gameId, userId, clientId, burialId, urlParams):
        sharePoint = hall_share3.getSharePointByBurialId(gameId, userId, clientId, burialId)
        share = cls.buildShare(gameId, userId, clientId, sharePoint, urlParams) if sharePoint else None
        mp = MsgPack()
        mp.setCmd('hall_share3')
        mp.setResult('action', 'get_burial_share')
        mp.setResult('gameId', gameId)
        mp.setResult('userId', userId)
        mp.setResult('burialId', burialId)
        mp.setResult('share', share)
        return mp

    @markCmdActionMethod(cmd='hall_share3', action='get_burial_share', clientIdVer=0)
    def doGetBurialShare(self, gameId, userId, clientId, burialId, urlParams):
        mp = self._doGetBurialShare(gameId, userId, clientId, burialId, urlParams)
        if mp:
            router.sendToUser(mp, userId)

    @classmethod
    def _doGetShareReward(cls, gameId, userId, clientId, pointId, whereToShare):
        ok, assetList = hall_share3.gainShareReward(gameId, userId, clientId, pointId, whereToShare)
        rewards = []
        if ok:
            for atup in assetList:
                rewards.append({'itemId': atup[0].kindId,
                                'name': atup[0].displayName,
                                'url': atup[0].pic,
                                'count': atup[1]})
        mp = MsgPack()
        mp.setCmd('hall_share3')
        mp.setResult('action', 'get_share_reward')
        mp.setResult('gameId', gameId)
        mp.setResult('userId', userId)
        mp.setResult('pointId', pointId)
        mp.setResult('rewards', rewards)
        return mp
    
    @markCmdActionMethod(cmd='hall_share3', action='get_share_reward', clientIdVer=0)
    def doGetShareReward(self, gameId, userId, clientId, pointId, whereToShare):
        mp = self._doGetShareReward(gameId, userId, clientId, pointId, whereToShare)
        if mp:
            router.sendToUser(mp, userId)
