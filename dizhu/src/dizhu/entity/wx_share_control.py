# -*- coding:utf-8 -*-
'''
Created on 2018-09-19

@author: wangyonghui

功能： 分享地域控制
'''
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from hall.entity.hallusercond import UserConditionRegister
from poker.entity.configure import configure
from sre_compile import isstring
from poker.entity.biz.exceptions import TYBizConfException
from poker.entity.dao import sessiondata
from poker.entity.events.tyevent import EventConfigure
import poker.entity.events.tyeventbus as pkeventbus
import freetime.util.log as ftlog
import poker.util.timestamp as pktimestamp


class ShareOrVideoConf(object):
    def __init__(self):
        self.type = None
        self.condition = None

    def decodeFromDict(self, d):
        self.type = d.get('type')
        if not isstring(self.type):
            raise TYBizConfException(d, 'WxShareControlConf.ShareOrVideoConf.type must be str')

        condition = d.get('condition')
        if not isinstance(condition, dict):
            raise TYBizConfException(d, 'WxShareControlConf.ShareOrVideoConf.condition must be dict')
        try:
            self.condition = UserConditionRegister.decodeFromDict(condition)
        except Exception, e:
            raise TYBizConfException(d, 'WxShareControlConf.ShareOrVideoConf.condition err=%s' % e.message)
        return self


class BurialIdConf(object):
    def __init__(self):
        self.burialId = None
        self.shareOrVideo = None

    def decodeFromDict(self, d):
        self.burialId = d.get('burialId')
        if not isstring(self.burialId):
            raise TYBizConfException(d, 'WxShareControlConf.BurialIdConf.burialId must be str')

        shareOrVideo = d.get('shareOrVideo')
        if not isinstance(shareOrVideo, list):
            raise TYBizConfException(d, 'WxShareControlConf.BurialIdConf.shareOrVideo must be list')
        self.shareOrVideo = [ShareOrVideoConf().decodeFromDict(d) for d in shareOrVideo]
        return self


class WxShareControlConf(object):
    def __init__(self):
        self.winStreakRewardSwitch = None
        self.matchRewardSwitch = None
        self.shareFakeSwitch = None
        self.burialIdList = None

    def decodeFromDict(self, d):
        self.winStreakRewardSwitch = d.get('winStreakRewardSwitch')
        if not isinstance(self.winStreakRewardSwitch, int):
            raise TYBizConfException(d, 'WxShareControlConf.winStreakRewardSwitch must be int')

        self.matchRewardSwitch = d.get('matchRewardSwitch')
        if not isinstance(self.matchRewardSwitch, int):
            raise TYBizConfException(d, 'WxShareControlConf.matchRewardSwitch must be int')

        self.shareFakeSwitch = d.get('shareFakeSwitch')
        if not isinstance(self.shareFakeSwitch, int):
            raise TYBizConfException(d, 'WxShareControlConf.shareFakeSwitch must be int')

        burialIdList = d.get('burialIdList')
        if not isinstance(burialIdList, list):
            raise TYBizConfException(d, 'WxShareControlConf.burialIdList must be list')
        self.burialIdList = [BurialIdConf().decodeFromDict(d) for d in burialIdList]
        return self


class WxShareControlHelper(object):
    @classmethod
    def getUserShareControlInfo(cls, userId):
        burialIdList = []
        clientId = sessiondata.getClientId(userId)
        for burialIdConf in _wxShareControlConf.burialIdList:
            sType = None
            for shareOrVideoConf in burialIdConf.shareOrVideo:
                if shareOrVideoConf.condition.check(DIZHU_GAMEID, userId, clientId, pktimestamp.getCurrentTimestamp()):
                    sType = shareOrVideoConf.type
                    break
            burialIdList.append({
                'burialId': burialIdConf.burialId,
                'shareOrVideo': sType
            })
        if ftlog.is_debug():
            ftlog.debug('WxShareControlHelper.getUserShareControlInfo userId=', userId,
                        'winStreakRewardSwitch=', _wxShareControlConf.winStreakRewardSwitch,
                        'matchRewardSwitch', _wxShareControlConf.matchRewardSwitch,
                        'shareFakeSwitch', _wxShareControlConf.shareFakeSwitch,
                        'burialIdList', burialIdList)
        return {
            'winStreakRewardSwitch': _wxShareControlConf.winStreakRewardSwitch,
            'matchRewardSwitch': _wxShareControlConf.matchRewardSwitch,
            'shareFakeSwitch': _wxShareControlConf.shareFakeSwitch,
            'burialIdList': burialIdList
        }


    @classmethod
    def getWinStreakRewardSwitch(cls):
        if ftlog.is_debug():
            ftlog.debug('WxShareControlHelper.getWinStreakRewardSwitch',
                        'winStreakRewardSwitch=', _wxShareControlConf.winStreakRewardSwitch)
        return _wxShareControlConf.winStreakRewardSwitch

    @classmethod
    def getMatchRewardSwitch(cls):
        if ftlog.is_debug():
            ftlog.debug('WxShareControlHelper.getMatchRewardSwitch',
                        'matchRewardSwitch=', _wxShareControlConf.matchRewardSwitch)
        return _wxShareControlConf.matchRewardSwitch

    @classmethod
    def getShareFakeSwitch(cls):
        if ftlog.is_debug():
            ftlog.debug('WxShareControlHelper.getShareFakeSwitch',
                        'shareFakeSwitch=', _wxShareControlConf.shareFakeSwitch)
        return _wxShareControlConf.shareFakeSwitch


_inited = False
_wxShareControlConf = None


def _reloadConf():
    global _wxShareControlConf
    conf = configure.getGameJson(DIZHU_GAMEID, 'wx.share.control', {})
    _wxShareControlConf = WxShareControlConf().decodeFromDict(conf)
    ftlog.info('wx_share_control._reloadConf success _wxShareControlConf=', _wxShareControlConf)


def _onConfChanged(event):
    if _inited and event.isChanged(['game:6:wx.share.control:0']):
        _reloadConf()


def _initialize():
    global _inited
    if not _inited:
        _inited = True
        _reloadConf()
        pkeventbus.globalEventBus.subscribe(EventConfigure, _onConfChanged)
    ftlog.info('wx_share_control._initialize ok')
