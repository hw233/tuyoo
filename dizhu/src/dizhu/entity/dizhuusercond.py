# -*- coding:utf-8 -*-
'''
Created on 2016年3月25日

@author: zhaojiangang
'''
from sre_compile import isstring

from dizhu.activitynew import activitysystemnew
import dizhu.activitynew.activitysystemnew as actsys
from dizhu.activitynew.buy_send_prize import BuySendPrize
from dizhu.entity import skillscore
from dizhu.entity.dizhuversion import SessionDizhuVersion
from dizhu.entity.erdayi import PlayerControl
import freetime.util.log as ftlog
from hall.entity.hallusercond import UserCondition, UserConditionRegister
from poker.entity.biz.exceptions import TYBizConfException
from poker.entity.biz.item.item import TYItemActionCondition, \
    TYItemActionConditionRegister
from poker.entity.dao import gamedata, userdata


class UserConditionDizhuDashifen(UserCondition):
    TYPE_ID = 'user.cond.dizhu.dashifen'
    def __init__(self):
        self.minScore = None
        self.maxScore = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        score = gamedata.getGameAttrInt(userId, gameId, 'skillscore')
        return (self.minScore == -1 or score >= self.minScore) \
            and (self.maxScore == -1 or score < self.maxScore)

    def decodeFromDict(self, d):
        self.minScore = d.get('minScore', -1)
        if not isinstance(self.minScore, int) or self.minScore < -1:
            raise TYBizConfException(d, 'UserConditionDizhuDashifen.minScore must be int >= -1')
        self.maxScore = d.get('maxScore', -1)
        if not isinstance(self.maxScore, int) or self.maxScore < -1:
            raise TYBizConfException(d, 'UserConditionDizhuDashifen.maxScore must be int >= -1')
        if self.maxScore != -1 and self.maxScore < self.minScore:
            raise TYBizConfException(d, 'UserConditionVipLevel.maxScore must >= minScore')
        return self

class UserConditionDizhuCanBuySendPrize(UserCondition):
    TYPE_ID = 'user.cond.dizhu.canBuySendPrize'
    def __init__(self):
        self.activityId = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        act = activitysystemnew.findActivity(self.activityId)
        if not act or not isinstance(act, BuySendPrize):
            return False
        return act.canSendPrize(userId, timestamp)

    def decodeFromDict(self, d):
        self.activityId = d.get('activityId')
        if not isstring(self.activityId) or not self.activityId:
            raise TYBizConfException(d, 'UserConditionDizhuCanBuySendPrize.activityId must be string')
        return self

class ItemActionConditionDizhuDashifenLevel(TYItemActionCondition):
    '''
    大师分等级
    '''
    TYPE_ID = 'item.action.cond.ddz.dashifen.level'
    def __init__(self):
        super(ItemActionConditionDizhuDashifenLevel, self).__init__()
        self.minLevel = None
        self.maxLevel = None

    def _conform(self, gameId, userAssets, item, timestamp, params):
        score = skillscore.get_skill_score(userAssets.userId)
        level = skillscore.get_skill_level(score)
        if ftlog.is_debug():
            ftlog.debug('ItemActionConditionDizhuDashifenLevel._conform gameId=', gameId,
                        'userId=', userAssets.userId,
                        'score=', score,
                        'level=', level,
                        'minLevel=', self.minLevel,
                        'maxLevel=', self.maxLevel)
        return (self.minLevel == -1 or level >= self.minLevel) \
            and (self.maxLevel == -1 or level < self.maxLevel)

    def decodeFromDict(self, d):
        super(ItemActionConditionDizhuDashifenLevel, self).decodeFromDict(d)
        self.minLevel = self.params.get('minLevel', -1)
        if not isinstance(self.minLevel, int) or self.minLevel < -1:
            raise TYBizConfException(self.params, 'UserConditionDizhuDashifen.params.minLevel must be int >= -1')
        self.maxLevel = self.params.get('maxLevel', -1)
        if not isinstance(self.maxLevel, int) or self.maxLevel < -1:
            raise TYBizConfException(self.params, 'UserConditionDizhuDashifenparams..maxLevel must be int >= -1')
        if self.maxLevel != -1 and self.maxLevel < self.minLevel:
            raise TYBizConfException(self.params, 'UserConditionVipLevel.params.maxLevel must >= minLevel')
        return self

class ItemActionConditionDizhuChargedRMB(TYItemActionCondition):
    TYPE_ID = 'item.action.cond.ddz.charged_rmb'

    def __init__(self):
        super(ItemActionConditionDizhuChargedRMB, self).__init__()
        self.autoReset = None
        self.rmbLimit = None
        self.chargeRmbRecorderActId = None

    def _conform(self, gameId, userAssets, item, timestamp, params):
        act = actsys.findActivity(self.chargeRmbRecorderActId)
        if not act:
            if ftlog.is_debug():
                ftlog.debug('ItemActionConditionDizhuChargedRMB._conform:act not found!',
                            'userId=', userAssets.userId,
                            'chargeRmbRecorderActId=', self.chargeRmbRecorderActId)
            return False
        model = act.loadModel(userAssets.userId)
        if ftlog.is_debug():
            ftlog.debug('ItemActionConditionDizhuChargedRMB._conform:',
                        'userId=', userAssets.userId,
                        'maxChargedMoney=', model.maxChargedMoney,
                        'rmbLimit=', self.rmbLimit,
                        'autoReset=', self.autoReset,
                        'return=', model.maxChargedMoney >= self.rmbLimit)
        # 若满足了充值数额，则将充值数额重置
        if model.maxChargedMoney >= self.rmbLimit:
            if self.autoReset:
                model.maxChargedMoney = 0
                act.saveModel(model)
            return True
        return False

    def decodeFromDict(self, d):
        super(ItemActionConditionDizhuChargedRMB, self).decodeFromDict(d)
        self.rmbLimit = self.params.get('rmbLimit', 0)
        if not isinstance(self.rmbLimit, int) or self.rmbLimit < 0:
            raise TYBizConfException(self.params, 'ItemActionConditionDizhuChargedRMB.params.rmbLimit must be int >= 0')

        self.autoReset = self.params.get('autoReset', 1)

        self.chargeRmbRecorderActId = self.params.get('chargeRmbRecorderActId')
        if not isinstance(self.chargeRmbRecorderActId, basestring):
            raise TYBizConfException(self.params, 'ItemActionConditionDizhuChargedRMB.params.chargeRmbRecorderActId must not be none')

        if ftlog.is_debug():
            ftlog.debug('ItemActionConditionDizhuChargedRMB.decodeFromDict:',
                        'd=', d,
                        'rmbLimit=', self.rmbLimit,
                        'autoReset=', self.autoReset,
                        'chargeRmbRecorderActId=', self.chargeRmbRecorderActId)
        return self

class UserConditionErdayiMasterscore(UserCondition):
    TYPE_ID = 'user.cond.erdayi.masterscore'
    def __init__(self):
        self.minScoreG = None
        self.maxScoreG = None
        self.minScoreS = None
        self.maxScoreS = None
        self.minScoreR = None
        self.maxScoreR = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):

        mo = PlayerControl.getMasterInfo(userId)
        if not mo:
            return False

        masterinfo = mo.getResult('rating')
        ftlog.debug('UserConditionErdayiMasterscore.check',
                    'userId=', userId,
                    'mo.code=', mo.getResult('code'),
                    'masterinfo=', masterinfo)
        if not masterinfo:
            return False

        ok = True
        g = float(masterinfo.get('g', '0.0'))
        s = float(masterinfo.get('s', '0.0'))
        r = float(masterinfo.get('r', '0.0'))

        ftlog.debug('UserConditionErdayiMasterscore.check',
                    'userId=', userId,
                    'minScoreG=', self.minScoreG,
                    'maxScoreG=', self.maxScoreG,
                    'minScoreS=', self.minScoreS,
                    'maxScoreS=', self.maxScoreS,
                    'minScoreR=', self.minScoreR,
                    'maxScoreR=', self.maxScoreR,
                    'g=', g, 's=', s, 'r=', r)

        if (self.minScoreG != None) and self.minScoreG > g:
            ok = False
        if (self.maxScoreG != None) and self.maxScoreG < g:
            ok = False

        if (self.minScoreS != None) and self.minScoreS > s:
            ok = False
        if (self.maxScoreS != None) and self.maxScoreS < s:
            ok = False

        if (self.minScoreR != None) and self.minScoreR > r:
            ok = False
        if (self.maxScoreR != None) and self.maxScoreR < r:
            ok = False

        ftlog.debug('UserConditionErdayiMasterscore.check',
                    'userId=', userId,
                    'ok=', ok)
        return ok

    def decodeFromDict(self, d):
        self.minScoreG = d.get('minScoreG')
        self.maxScoreG = d.get('maxScoreG')

        self.minScoreS = d.get('minScoreS')
        self.maxScoreS = d.get('maxScoreS')

        self.minScoreR = d.get('minScoreR')
        self.maxScoreR = d.get('maxScoreR')
        return self

class UserConditionDizhuClientVersion(UserCondition):
    TYPE_ID = 'user.cond.dizhu.clientVer'
    def __init__(self):
        self.minVersion = None
        self.maxVersion = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        clientVer = SessionDizhuVersion.getVersionNumber(userId)
        return (self.minVersion is None or clientVer >= self.minVersion) \
            and (self.maxVersion is None or clientVer < self.maxVersion)

    def decodeFromDict(self, d):
        self.minVersion = d.get('minVersion')
        self.maxVersion = d.get('maxVersion')

        if (self.minVersion is not None
            and not isinstance(self.minVersion, (int, float))):
            raise TYBizConfException(d, 'UserConditionDizhuClientVersion.minVersion must be int or float')
        if (self.maxVersion is not None
            and not isinstance(self.maxVersion, (int, float))):
            raise TYBizConfException(d, 'UserConditionDizhuClientVersion.maxVersion must be int or float')
        if (self.minVersion is not None
            and self.maxVersion is not None
            and self.maxVersion < self.minVersion):
            raise TYBizConfException(d, 'UserConditionDizhuClientVersion.maxVersion must >= minVersion')
        return self

class UserConditionDizhuTableShareToday(UserCondition):
    TYPE_ID = 'user.cond.dizhu.table.share'

    '''
    此条件使用activitynew/table_share_recorder活动记录的玩家牌局分享次数做条件判断，若要此条件正常工作，活动务必不能过期
    {
     "typeId":"user.cond.dizhu.table.share",
     "tableShareRecorderActId": "table_share_recorder1", // 关联的活动ID
     "tableShareCount": 1 // 最少要达到的分享次数
    }
    '''
    def __init__(self):
        self.tableShareRecorderActId = 0
        self.tableShareCount = 1

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        act = actsys.findActivity(self.tableShareRecorderActId)
        if ftlog.is_debug():
            ftlog.debug('UserConditionDizhuTableShareToday.check:',
                        'userId=', userId,
                        'tableShareRecorderActId=', self.tableShareRecorderActId,
                        'tableShareCount=', self.tableShareCount)
        if not act:
            if ftlog.is_debug():
                ftlog.debug('UserConditionDizhuTableShareToday.check:act not found!', userId)
            return False
        return act.getTodaySharedCount(userId) >= self.tableShareCount

    def decodeFromDict(self, d):
        self.tableShareRecorderActId = d.get('tableShareRecorderActId')
        if self.tableShareRecorderActId == None or not isstring(self.tableShareRecorderActId):
            raise TYBizConfException(d, 'UserConditionDizhuTableShareToday.tableShareRecorderActId must be string')

        self.tableShareCount = d.get('tableShareCount', 1)
        if self.tableShareCount <= 0 or not isinstance(self.tableShareCount, int):
            raise TYBizConfException(d, 'UserConditionDizhuTableShareToday.tableShareCount must be int')
        return self

class UserConditionFTTableFinish(UserCondition):
    TYPE_ID = 'user.cond.dizhu.fttable.finish'

    '''
    此条件使用activitynew/table_share_recorder活动记录的玩家牌局分享次数做条件判断，若要此条件正常工作，活动务必不能过期
    {
     "typeId":"user.cond.dizhu.fttable.finish",
     "actId": "fttable_finish_recorder1", // 关联的活动ID
     "finishCount": 1 // 完成朋友场次数
    }
    '''
    def __init__(self):
        self.actId = None
        self.finishCount = 1

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        act = actsys.findActivity(self.actId)
        if ftlog.is_debug():
            ftlog.debug('UserConditionFTTableFinish.check',
                        'userId=', userId,
                        'actId=', self.actId,
                        'finishCount=', self.finishCount)
        if not act:
            if ftlog.is_debug():
                ftlog.debug('UserConditionFTTableFinish.check ActNotFound',
                            'userId=', userId,
                            'actId=', self.actId,
                            'finishCount=', self.finishCount)
            return False
        model = act.loadModel(userId, timestamp)
        return model.finishCount >= self.finishCount

    def decodeFromDict(self, d):
        self.actId = d.get('actId')
        if not self.actId or not isstring(self.actId):
            raise TYBizConfException(d, 'UserConditionFTTableFinish.actId must be string')

        self.finishCount = d.get('finishCount', 1)
        if not isinstance(self.finishCount, int):
            raise TYBizConfException(d, 'UserConditionFTTableFinish.finishCount must be int')
        return self

class UserConditionLimitProvince(UserCondition):
    TYPE_ID = 'user.cond.limitProvince'

    def __init__(self):
        self.limitProvinces = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        if not self.limitProvinces:
            return False
        province = userdata.getAttr(userId, 'province')
        if not province:
            return False
        try:
            province = province.encode('utf8') if isinstance(province, unicode) else province
        except:
            return False
        if province in self.limitProvinces:
            return True
        return False

    def decodeFromDict(self, d):
        self.limitProvinces = d.get('limitProvinces')
        return self


class UserConditionAlwaysTrue(UserCondition):
    TYPE_ID = 'user.cond.alwaysTrue'

    def __init__(self):
        pass

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        return True

    def decodeFromDict(self, d):
        return self


class UserConditionAlwaysFalse(UserCondition):
    TYPE_ID = 'user.cond.alwaysFalse'

    def __init__(self):
        pass

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        return False

    def decodeFromDict(self, d):
        return self


class UserConditionInProvinces(UserCondition):
    TYPE_ID = 'user.cond.inProvinces'

    def __init__(self):
        super(UserConditionInProvinces, self).__init__()
        self.provinces = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        # 通过 userId 获取用户位置信息
        userProvince = userdata.getAttr(userId, 'province')
        if not userProvince:
            return False

        try:
            userProvince = userProvince.encode('utf8') if isinstance(userProvince, unicode) else userProvince
        except:
            return False

        if ftlog.is_debug():
            isInProvince = False
            for province in self.provinces:
                if province in userProvince:
                    isInProvince = True
            ftlog.debug('UserConditionInProvinces userId=', userId,
                        'userProvince=', userProvince,
                        'provinces=', self.provinces,
                        'isInProvince=', isInProvince)

        for province in self.provinces:
            if province in userProvince:
                return True
        return False

    def decodeFromDict(self, d):
        provinces = d.get('provinces', [])
        self.provinces = provinces
        return self


class UserConditionNotInProvinces(UserCondition):
    TYPE_ID = 'user.cond.notInProvinces'

    def __init__(self):
        super(UserConditionNotInProvinces, self).__init__()
        self.provinces = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        # 通过 userId 获取用户位置信息
        userProvince = userdata.getAttr(userId, 'province')
        if not userProvince:
            return False

        try:
            userProvince = userProvince.encode('utf8') if isinstance(userProvince, unicode) else userProvince
        except:
            return False

        if ftlog.is_debug():
            isNotInProvince = True
            for province in self.provinces:
                if province in userProvince:
                    isNotInProvince = False
            ftlog.debug('UserConditionNotInProvinces userId=', userId,
                        'userProvince=', userProvince,
                        'provinces=', self.provinces,
                        'isNotInProvince=', isNotInProvince)

        for province in self.provinces:
            if province in userProvince:
                return False
        return True

    def decodeFromDict(self, d):
        provinces = d.get('provinces', [])
        self.provinces = provinces
        return self


class UserConditionInCities(UserCondition):
    TYPE_ID = 'user.cond.inCities'

    def __init__(self):
        super(UserConditionInCities, self).__init__()
        self.cities = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        # 通过 userId 获取用户位置信息
        userProvince = userdata.getAttr(userId, 'province')
        if not userProvince:
            return False
        try:
            userProvince = userProvince.encode('utf8') if isinstance(userProvince, unicode) else userProvince
        except:
            return False

        if ftlog.is_debug():
            ftlog.debug('UserConditionInCities userId=', userId,
                        'userProvince=', userProvince,
                        'cities=', self.cities,
                        'isInCities=', userProvince in self.cities)

        if userProvince in self.cities:
            return True
        return False

    def decodeFromDict(self, d):
        cities = d.get('cities', [])
        self.cities = cities
        return self


class UserConditionNotInCities(UserCondition):
    TYPE_ID = 'user.cond.notInCities'

    def __init__(self):
        super(UserConditionNotInCities, self).__init__()
        self.cities = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        # 通过 userId 获取用户位置信息
        userProvince = userdata.getAttr(userId, 'province')
        if not userProvince:
            return False
        try:
            userProvince = userProvince.encode('utf8') if isinstance(userProvince, unicode) else userProvince
        except:
            return False

        if ftlog.is_debug():
            ftlog.debug('UserConditionNotInCities userId=', userId,
                        'userProvince=', userProvince,
                        'cities=', self.cities,
                        'isNotInCities=', userProvince not in self.cities)

        if userProvince not in self.cities:
            return True
        return False

    def decodeFromDict(self, d):
        cities = d.get('cities', [])
        self.cities = cities
        return self


class UserConditionDayShareTimes(UserCondition):
    TYPE_ID = 'user.cond.dayShare'

    def __init__(self):
        super(UserConditionDayShareTimes, self).__init__()
        self.start = None
        self.end = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        from dizhu.entity.dizhu_share_count import getDayShareTimes
        dayShareTimes = getDayShareTimes(userId)
        if (self.start == -1 or dayShareTimes >= self.start) and (self.end == -1 or dayShareTimes <= self.end):
            return True
        return False

    def decodeFromDict(self, d):
        self.start = d.get('start')
        if not isinstance(self.start, int):
            raise TYBizConfException(d, 'UserConditionDayShareTimes.start must be int')

        self.end = d.get('end')
        if not isinstance(self.end, int):
            raise TYBizConfException(d, 'UserConditionDayShareTimes.end must be int')
        return self


class UserConditionTotalShareTimes(UserCondition):
    TYPE_ID = 'user.cond.totalShare'

    def __init__(self):
        super(UserConditionTotalShareTimes, self).__init__()
        self.start = None
        self.end = None

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        from dizhu.entity.dizhu_share_count import getTotalShareTimes
        totalShareTimes = getTotalShareTimes(userId)
        if (self.start == -1 or totalShareTimes >= self.start) and (self.end == -1 or totalShareTimes <= self.end):
            return True
        return False

    def decodeFromDict(self, d):
        self.start = d.get('start')
        if not isinstance(self.start, int):
            raise TYBizConfException(d, 'UserConditionTotalShareTimes.start must be int')

        self.end = d.get('end')
        if not isinstance(self.end, int):
            raise TYBizConfException(d, 'UserConditionTotalShareTimes.end must be int')
        return self

class UserConditionHengban(UserCondition):
    TYPE_ID = 'user.cond.hengban'

    def __init__(self):
        pass

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        if clientId == 'H5_5.1_weixin.weixin.0-hall6.weixin.tuyoo':
            return True
        return False

    def decodeFromDict(self, d):
        return self


class UserConditionShuban(UserCondition):
    TYPE_ID = 'user.cond.shuban'

    def __init__(self):
        pass

    def check(self, gameId, userId, clientId, timestamp, **kwargs):
        if clientId == 'H5_5.1_weixin.weixin.0-hall6.weixin.huanle':
            return True
        return False

    def decodeFromDict(self, d):
        return self

def _registerClasses():
    ftlog.debug('dizhuusercond._registerClasses')
    UserConditionRegister.registerClass(UserConditionDizhuDashifen.TYPE_ID, UserConditionDizhuDashifen)
    UserConditionRegister.registerClass(UserConditionDizhuCanBuySendPrize.TYPE_ID, UserConditionDizhuCanBuySendPrize)
    UserConditionRegister.registerClass(UserConditionErdayiMasterscore.TYPE_ID, UserConditionErdayiMasterscore)
    UserConditionRegister.registerClass(UserConditionDizhuClientVersion.TYPE_ID, UserConditionDizhuClientVersion)
    UserConditionRegister.registerClass(UserConditionDizhuTableShareToday.TYPE_ID, UserConditionDizhuTableShareToday)
    UserConditionRegister.registerClass(UserConditionFTTableFinish.TYPE_ID, UserConditionFTTableFinish)
    UserConditionRegister.registerClass(UserConditionLimitProvince.TYPE_ID, UserConditionLimitProvince)
    UserConditionRegister.registerClass(UserConditionAlwaysTrue.TYPE_ID, UserConditionAlwaysTrue)
    UserConditionRegister.registerClass(UserConditionAlwaysFalse.TYPE_ID, UserConditionAlwaysFalse)

    UserConditionRegister.registerClass(UserConditionInProvinces.TYPE_ID, UserConditionInProvinces)
    UserConditionRegister.registerClass(UserConditionNotInProvinces.TYPE_ID, UserConditionNotInProvinces)
    UserConditionRegister.registerClass(UserConditionInCities.TYPE_ID, UserConditionInCities)
    UserConditionRegister.registerClass(UserConditionNotInCities.TYPE_ID, UserConditionNotInCities)

    UserConditionRegister.registerClass(UserConditionDayShareTimes.TYPE_ID, UserConditionDayShareTimes)
    UserConditionRegister.registerClass(UserConditionTotalShareTimes.TYPE_ID, UserConditionTotalShareTimes)

    UserConditionRegister.registerClass(UserConditionHengban.TYPE_ID, UserConditionHengban)
    UserConditionRegister.registerClass(UserConditionShuban.TYPE_ID, UserConditionShuban)

    TYItemActionConditionRegister.registerClass(ItemActionConditionDizhuDashifenLevel.TYPE_ID, ItemActionConditionDizhuDashifenLevel)
    TYItemActionConditionRegister.registerClass(ItemActionConditionDizhuChargedRMB.TYPE_ID, ItemActionConditionDizhuChargedRMB)


