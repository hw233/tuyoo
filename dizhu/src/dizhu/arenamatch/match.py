# -*- coding:utf-8 -*-
'''
Created on 2015年12月1日

@author: zhaojiangang
'''
import random

from dizhu.arenamatch.interfacedizhu import MatchPlayerNotifierDizhu, \
    MatchTableControllerDizhu, MatchRankRewardsSenderDizhu, UserInfoLoaderDizhu, \
    SigninFeeDizhu, SigninRecordDaoDizhu, UserLockerDizhu
from dizhu.entity import dizhuaccount, dizhuhallinfo
from dizhu.entity.dizhualert import Alert
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.matchhistory import MatchHistoryHandler
from dizhu.entity.matchrecord import MatchRecord
from dizhu.gameplays import punish
from freetime.core.tasklet import FTTasklet
from freetime.entity.msg import MsgPack
from freetime.util.log import getMethodName
import freetime.util.log as ftlog
from hall.entity import  hallpopwnd
from hall.entity import hallstore, hallitem, hallconf
from hall.entity.todotask import TodoTaskShowInfo, TodoTaskHelper, \
    TodoTaskOrderShow
from poker.entity.configure import configure, gdata
from poker.entity.dao import sessiondata, userdata, gamedata
from poker.entity.game.rooms.arena_match_ctrl.exceptions import \
    SigninFeeNotEnoughException, SigninNotStartException, SigninStoppedException, \
    SigninFullException, MatchExpiredException, ClientVersionException, \
    MatchSigninConditionException
from poker.entity.game.rooms.arena_match_ctrl.match import Match, MatchInstance, \
    MatchPlayer
from poker.entity.game.rooms.big_match_ctrl.const import MatchType
from poker.entity.game.rooms.big_match_ctrl.matchif import MatchIF
from poker.protocol import router
from poker.protocol import runcmd
from poker.util import strutil


class ArenaMatchIF(MatchIF):
    # key=roomId, value=Match
    _matchMap = {}
    WINLOSE_SLEEP = 2
    
    @classmethod
    def getMatch(cls, roomId):
        return cls._matchMap.get(roomId, None)
    
    @classmethod
    def setMatch(cls, roomId, match):
        cls._matchMap[roomId] = match
    
    @classmethod
    def buildMatch(cls, conf, room):
        match = Match(conf)
        
        match.tableController = MatchTableControllerDizhu(room)
        match.playerNotifier = MatchPlayerNotifierDizhu(room, cls)
        match.matchRewardsSender = MatchRankRewardsSenderDizhu(room)
        match.userInfoLoader = UserInfoLoaderDizhu()
        match.signinFee = SigninFeeDizhu(room)
        match.signinRecordDao = SigninRecordDaoDizhu(room)
        match.userLocker = UserLockerDizhu()
        return match
    
    @classmethod
    def translateState(cls, state):
        if (state < MatchInstance.STATE_STARTED):
            return 0
        if (state < MatchInstance.STATE_STOP):
            return 10
        return 20
    
    @classmethod
    def calcMatchDuration(cls, conf):
        totalCardCount = 0
        for stage in conf.stages:
            totalCardCount += stage.cardCount
        return totalCardCount * 120
    
    @classmethod
    def buildRewards(cls, rankRewards):
        ret = []
        for r in rankRewards.rewards:
            if r.count > 0:
                name = hallconf.translateAssetKindIdToOld(r.assetKindId)
                ret.append({'name':name or '', 'count':r.count})
        return ret
    
    @classmethod
    def buildRewardsDesc(cls, rankRewards):
        notNeedDescNames = set(['user:chip', 'user:coupon', 'ddz.exp'])
        allZero = True
        for r in rankRewards.rewards:
            if r['count'] <= 0:
                continue
            if r['itemId'] not in notNeedDescNames:
                return rankRewards.desc
            #allZero = False# #此处为了兼容3.x版本不显示rewardDesc
        return rankRewards.desc if allZero else None
    
    @classmethod
    def buildRankRewards(cls, rankRewardsList, defaultEnd = 10000):
        ret = []
        notNeedShow = set(['user:charm', 'user:exp', 'game:assistance'])
        for rankRewards in rankRewardsList:
            rewardDesc = cls.buildRewardsDesc(rankRewards)
            rewardsList = [] # 奖励信息列表 [{name,num,unit,decs,img},{"电饭煲","1","台","电饭煲x1台","${http_download}/hall/item/imgs/item_1017.png"}]
            for r in rankRewards.rewards:
                assetKind = hallitem.itemSystem.findAssetKind(r['itemId'])
                if r['count'] > 0 and assetKind and r['itemId'] not in notNeedShow:
                    rewardsList.append({'name': assetKind.displayName,
                                        'num': r['count'],
                                        'unit': assetKind.units,
                                        'desc': assetKind.displayName + 'x' + str(r['count']) + assetKind.units,
                                        'img': assetKind.pic
                                        })
            if rewardDesc:
                ret.append({
                            'range':{'s':rankRewards.startRank, 'e':rankRewards.endRank if rankRewards.endRank > 0 else defaultEnd},
                            'rewards':[], #此处为了兼容3.x版本不显示rewardDesc，cls.buildRewards(rankRewards),
                            'rewardsDesc':rewardDesc,
                            'rewardsList':rewardsList
                            })
            else:
                ret.append({
                            'range':{'s':rankRewards.startRank, 'e':rankRewards.endRank if rankRewards.endRank > 0 else defaultEnd},
                            'rewards':cls.buildRewards(rankRewards),
                            'rewardsList':rewardsList
                            })
        return ret

    @classmethod
    def buildAssetKindMap(cls):
        assetKindMap = {} # 道具map
        assetKindConfList = hallconf.getItemConf().get('assets', []) # 所有道具配置表
        for assetKindConf in assetKindConfList:
            if assetKindConf.get('kindId'):
                assetKindMap[assetKindConf.get('kindId')] = assetKindConf
        itemKindConfList = hallconf.getItemConf().get('items', [])
        for itemKindConf in itemKindConfList:
            if itemKindConf.get('kindId'):
                assetKindMap['item:' + str(itemKindConf.get('kindId'))] = {
                    "kindId":'item:' + str(itemKindConf.get('kindId')),
                    "displayName":itemKindConf.get('displayName', ''),
                    "pic":itemKindConf.get('pic', ''),
                    "units":itemKindConf.get('units', '').get('displayName', '') if itemKindConf.get('units', '') else ''
                }
        return assetKindMap

    @classmethod
    def buildStages(cls, stages):
        '''
        stage.name 必须由这些字组成 {'0' '1' '2' '3' '4' '5' '6' '7' '8' '9' 
        '比' '第' '分' '海' '级' '晋' '决' '轮' '强' '赛' '选' '总' '组'}
        '''
        ret = []
        for stage in stages:
            matchName = ''
            n = -1
            dec = '%s人晋级' % (stage.riseUserCount)
            if stage.name.find('海选赛') != -1:
                matchName = 'haixuansai'
            elif stage.name.find('晋级赛') != -1:
                matchName = 'jinjisai'
            elif stage.name.find('分组赛') != -1:
                matchName = 'fenzusai'
            elif stage.name.find('强赛') != -1:
                matchName = 'n_qiangsai'
                n = int(stage.name[0:stage.name.find('强赛')])
            elif stage.name.find('总决赛') != -1:
                matchName = 'zongjuesai'
            elif stage.name.find('决赛') != -1:
                matchName = 'juesai'
            ret.append({'isPass':False, 'stationType':matchName, 'n':n, 'isHere':False, 'description': dec, 'name':stage.name})
        return ret

    @classmethod
    def buildFeesList(cls, userId, fees):
        ret = [] # 返回付费列表[{type,desc,selected,img}，{...}]
        # 不用写单位的道具类型集合
        notNeedUnit = set(['user:chip', 'user:exp', 'user:charm', 'ddz:master.score']);
        for fee in fees:
            assetKind = hallitem.itemSystem.findAssetKind(fee.assetKindId)
            if fee.count > 0 and assetKind:
                desc = ''
                if fee.assetKindId in notNeedUnit:
                    desc = str(fee.count) + assetKind.displayName
                else:
                    desc = str(fee.count) + assetKind.units + assetKind.displayName
                from dizhu.activities.toolbox import UserBag
                myCount = UserBag.getAssetsCount(userId, fee.assetKindId)
                ret.append({'type':fee.assetKindId, 'desc':desc, 'img':assetKind.pic, 'selected':False, 'fulfilled':1 if myCount >= fee.count else 0})
        return ret

    @classmethod
    def getMatchInfo(cls, room, uid, mo):
        match = cls.getMatch(room.roomId)
        if not match:
            mo.setError(1, 'not a match room')
            return

        inst = match.currentInstance
        if not inst:
            return
        
        conf = inst.matchConf if inst else match.matchConf

        info = {}
        info['roomId'] = room.roomId
        info['type'] = MatchType.USER_COUNT
        info['name'] = room.roomConf["name"]
        info['minPlayer'] = info['maxPlayer'] = conf.stages[0].totalUserCount
        info['state'] = cls.translateState(inst.state)
        info['curTimeLeft'] = 0
        mo.setResult('info', info)
        mo.setResult('startTime', '')

        matchDuration = int(cls.calcMatchDuration(conf) / 60)
        mo.setResult('rankRewards', cls.buildRankRewards(conf.rankRewardsList))
        mo.setResult('duration', '约%d分钟' % (min(30, matchDuration)))
            
        mo.setResult('tips', {'infos':conf.tips.infos,
                              'interval':conf.tips.interval
                              })
        
        record = MatchRecord.loadRecord(room.gameId, uid, match.matchId)
        if record:
            mo.setResult('mrecord', {'bestRank':record.bestRank,
                                     'bestRankDate':record.bestRankDate,
                                     'isGroup':record.isGroup,
                                    'crownCount':record.crownCount,
                                    'playCount':record.playCount})
        mo.setResult('fees', [])
        # 报名费列表
        mo.setResult('feesList', cls.buildFeesList(uid, conf.fees))
        # 分组赛奖励列表 arena_match没有分组奖励
        mo.setResult('groupRewardList', [])
        # 比赛进程 海选赛-》分组赛-》8强赛-》总决赛
        stagesList = cls.buildStages(conf.stages) if conf.stages else []
        mo.setResult('stages', stagesList)
        # 比赛报名的前提条件
        conditionDesc = cls.getMatchConditionDesc(room.roomId, uid)
        if conditionDesc:
            mo.setResult('conditionDesc', conditionDesc)
        # 比赛奖励分割线文字
        mo.setResult('splitWord', cls.getMatchRewardSplitWord(room.roomId))
        # 获得比赛历史数据
        mo.setResult('hisitory', MatchHistoryHandler.getMatchHistory(uid, match.matchConf.recordId))


    # 获取比赛分组奖励与非分组奖励之间分割线的描述文字
    @classmethod
    def getMatchRewardSplitWord(cls, roomId):
        ret = "以下是分组阶段未晋级名次奖励"
        splitConf = configure.getGameJson(DIZHU_GAMEID, 'room.split', {})
        if not splitConf:
            return ret
        bigRoomId = gdata.getBigRoomId(roomId)
        roomConf = splitConf.get(str(bigRoomId))
        if not roomConf:
            roomConf = splitConf.get('default')
        if not roomConf:
            return ret
        word = roomConf.get('splitWord')
        from sre_compile import isstring
        if not word or not isstring(word):
            return ret
        ret = word
        return ret


    # 获取比赛前提条件描述
    @classmethod
    def getMatchConditionDesc(cls, roomId, userId):
        matchCondConf = configure.getGameJson(DIZHU_GAMEID, 'bigmatch.filter', {})
        if not matchCondConf:
            if ftlog.is_debug():
                ftlog.debug('bigmatch EmptyMatchCondConf roomId=', roomId,
                        'gameId=', DIZHU_GAMEID,
                        'userId=', userId,
                        'matchCondConf=', matchCondConf)
            return None
        bigRoomId = gdata.getBigRoomId(roomId)
        condConf = matchCondConf.get(str(bigRoomId))
        if not condConf:
            if ftlog.is_debug():
                ftlog.debug('bigmatch EmptyCondConf roomId=', roomId,
                            'gameId=', DIZHU_GAMEID,
                            'userId=', userId,
                            'bigRoomId=', bigRoomId,
                            'condConf=', condConf,
                            'matchCondConf=', matchCondConf)
            return None
        else:
            ftlog.debug('bigmatch CondConf roomId=', roomId,
                    'bigRoomId=', bigRoomId,
                    'gameId=', DIZHU_GAMEID,
                    'userId=', userId,
                    'matchCondConf=', matchCondConf)
        condition = condConf.get('condition')
        if not condition:
            if ftlog.is_debug():
                ftlog.debug('bigmatch EmptyCondition roomId=', roomId,
                            'gameId=', DIZHU_GAMEID,
                            'userId=', userId,
                            'matchCondConf=', matchCondConf)
            return None
        desc = condition.get('desc')
        if not desc:
            if ftlog.is_debug():
                ftlog.debug('bigmatch EmptyMatchCondConf.condition.desc roomId=', roomId,
                        'gameId=', DIZHU_GAMEID,
                        'userId=', userId,
                        'matchCondConf=', matchCondConf)
            return None
        from sre_compile import isstring
        if not isstring(desc):
            if ftlog.is_debug():
                ftlog.debug('bigmatch EmptyMatchCondConf.condition.desc roomId=', roomId,
                        'gameId=', DIZHU_GAMEID,
                        'userId=', userId,
                        'matchCondConf=', matchCondConf)
            return None
        return desc


    # @classmethod
    # def getPublicMatchConfig(cls):
    #     from dizhu.entity import dizhuconf
    #     return dizhuconf.getPublic().get('match_v3_77', {})
    
    @classmethod
    def checkTime(cls, startTime, stopTime):
        if not startTime or not stopTime:
            return True
        from datetime import datetime
        time_now = datetime.now().time()
        
        time_start = datetime.strptime(startTime, '%H:%M').time()
        time_end = datetime.strptime(stopTime, '%H:%M').time()
        
        # 今天的启示时间点到明天的终止时间点
        if time_start >= time_end:
            return time_start <= time_now or time_now < time_end
        return time_start <= time_now and time_now < time_end


    @classmethod
    def getMatchStates(cls, room, userId, player, mo):
        match = cls.getMatch(room.roomId)
        if not match:
            mo.setError(1, u'非比赛房间')
            return
        if player and player.matchInst.match != match:
            mo.setError(1, u'非比赛房间')
            ftlog.warn('ArenaMatchIF.getMatchStates room=', room.roomId,
                       'matchId=', match.matchId,
                       'userId=', userId,
                       'player.match=', player.matchInst.matchId,
                       'diff match')
            return
        inst = player.matchInst if player else match.currentInstance
        state = cls.translateState(inst.state) if inst else 0
        mo.setResult('roomId', room.roomId)
        mo.setResult('state', state)
        curPlayer = 0
        if player and player.stage:
            curPlayer = player.stage.stageConf.totalUserCount
        else:
            if inst and inst.state == MatchInstance.STATE_STARTED:
                maxUserCount = int(inst.matchConf.stages[0].totalUserCount)
                minUserCount = maxUserCount - max(1, int(maxUserCount * 0.15))
                curPlayer = random.randint(minUserCount, maxUserCount - 1)#inst.getSigninCount()
                
        mo.setResult('inst', inst.instId)
        mo.setResult('curPlayer', curPlayer)
        mo.setResult('curTimeLeft', 0)
        mo.setResult('startTime', '')

        bigRoomId = gdata.getBigRoomId(room.roomId)
        roomInfo = dizhuhallinfo.loadAllRoomInfo(DIZHU_GAMEID).get(bigRoomId)
        roomconf = gdata.getRoomConfigure(bigRoomId)

        peopleNumberBase = max(roomInfo.playerCount, roomInfo.signinCount)
        peopleNumber = max(peopleNumberBase*9 - random.randint(80, 88), 0)
        startTime = roomconf.get('matchConf',{}).get('startTime')
        stopTime = roomconf.get('matchConf',{}).get('stopTime')
        # Arena比赛在开赛时间之内
        if cls.checkTime(startTime, stopTime):
            mo.setResult('onlinePlayerCount', peopleNumber)
            mo.setResult('signinPlayerCount', peopleNumber)
        else:
            mo.setResult('onlinePlayerCount', roomInfo.playerCount if roomInfo else 0)
            mo.setResult('signinPlayerCount', roomInfo.signinCount if roomInfo else 0)

        if ftlog.is_debug():
            ftlog.debug('ArenaMatchIF.getMatchStates room=', room.roomId,
                        'matchId=', match.matchId,
                        'userId=', userId,
                        'player=', player,
                        'stageIndex=', player.stage.index if player and player.stage else -1)
        
        if not player or not player.stage:
            return
        
        tcount = 1
        allcount = player.stage.stageConf.totalUserCount
        rank = player.rank
        if player.seat:
            rank = player.tableDisplayRank
        waitInfo = {
            'uncompleted':tcount, # 还有几桌未完成
            'tableRunk':'%d/3' % player.tableRank, # 本桌排名
            'runk':'%d/%d' % (rank, allcount), # 总排名
            'chip':player.score, # 当前积分
        }
        if player.state == MatchPlayer.STATE_WAIT and player.stage.index != 0:
            waitInfo['info'] = '您已经成功晋级，请等待其他玩家完成本轮比赛'
        mo.setResult('waitInfo', waitInfo)
        mo.setResult('progress', 0)

    @classmethod
    def handleMatchException(cls, room, ex, uid, mo):
        ftlog.warn(getMethodName(), "<<|roomId, userId:", room.roomId, uid, ex.message)
        if isinstance(ex, SigninFeeNotEnoughException):
            cls._handleSigninFeeNotEnoughException(room, ex, uid, mo)
        elif isinstance(ex, (SigninNotStartException,
                             SigninStoppedException,
                             SigninFullException,
                             MatchExpiredException,
                             ClientVersionException,
                             MatchSigninConditionException)):
            cls._handleSigninException(room, ex, uid, mo)
        else:
            mo.setError(ex.errorCode, ex.message)
            router.sendToUser(mo, uid)
    
    @classmethod
    def doWinLose(cls, room, table, seatId, isTimeOutKill=False): # TODO:
        if not table._match_table_info:
            ftlog.warn('ArenaMatchIF.doWinLose roomId=', room.roomId,
                       'tableId=', table.tableId,
                       'seatId=', seatId, 'isTimeOutKill=', isTimeOutKill,
                       'not matchTableInfo')
            return
        
        # 计算春天
        dizhuseatId = table.status.diZhu
        if seatId != dizhuseatId: 
            if table.seats[dizhuseatId - 1].outCardCount == 1:
                table.status.chuntian = 2
        else:
            s1 = table.seats[(dizhuseatId - 1 + 1) % table.maxSeatN]
            s2 = table.seats[(dizhuseatId - 1 + 2) % table.maxSeatN]
            if s1.outCardCount == 0 and s2.outCardCount == 0:
                table.status.chuntian = 2
                 
        # 翻倍计算 叫地主的倍数
        windoubles = table.status.callGrade
        # 炸弹倍数
        windoubles *= pow(2, table.status.bomb)
        # 春天倍数
        windoubles *= table.status.chuntian
        # 底牌倍数
        windoubles *= table.status.baseCardMulti
        # 明牌倍数
        windoubles *= table.status.show
         
        dizhuwin = 0
        if seatId == dizhuseatId:
            dizhuwin = 1
        if seatId == 0 : # 流局
            dizhuwin = 0
            windoubles = 1
        else:
            windoubles = abs(windoubles)
 
        userids = []
        detalChips = []
        seat_coin = []
        baseBetChip = table._match_table_info['baseScore']
        robot_card_count = [0] * len(table.seats)  # 每个座位
        for x in xrange(len(table.seats)):
            uid = table.seats[x].userId
            userInfo = table._match_table_info['userInfos'][x]
            userids.append(uid)
            if seatId == 0 : # 流局
                detalChip = -baseBetChip
            else:
                if dizhuwin :
                    if x + 1 == dizhuseatId :
                        detalChip = baseBetChip + baseBetChip
                    else:
                        detalChip = -baseBetChip
                else:
                    if x + 1 == dizhuseatId :
                        detalChip = -baseBetChip - baseBetChip
                    else:
                        detalChip = baseBetChip
            detalChip *= windoubles
            detalChips.append(detalChip)
            seat_coin.append(userInfo['score'] + detalChip)
            robot_card_count[x] = table.seats[x].robotCardCount
            ftlog.info('dizhu.game_win userId=', uid, 'roomId=', room.roomId, 'tableId=', table.tableId, 'delta=', detalChip)
        
        ftlog.debug('doWinLose->after room fee->robot_card_count=', robot_card_count)
#         table.punishClass().doWinLosePunish(table, seat_coin, detalChips)
        punish.Punish.doWinLosePunish(table.runConfig.punishCardCount, table.runConfig.isMatch,
                                      seat_coin, detalChips, robot_card_count)
        for x in xrange(len(table.seats)):
            uid = table.seats[x].userId
            userInfo = table._match_table_info['userInfos'][x]
            userInfo['score'] = seat_coin[x]
        
        # 返回当前Table的game_win
        moWin = MsgPack()
        moWin.setCmd('table_call')
        moWin.setResult('action', 'game_win')
        moWin.setResult('isMatch', 1)
        moWin.setResult('gameId', table.gameId)
        moWin.setResult('roomId', table.roomId)
        moWin.setResult('tableId', table.tableId)
#         moWin.setResult('stat', dict(zip(tdz_stat_title, table.status)))
        moWin.setResult('stat', table.status.toInfoDictExt())
        moWin.setResult('dizhuwin', dizhuwin)
        if seatId == 0:
            moWin.setResult('nowin', 1)
        moWin.setResult('slam', 0)
        moWin.setResult('cards', [seat.cards for seat in table.seats])
 
        roundId = table.gameRound.number
        table.clear(userids)
         
        for x in xrange(len(userids)):
            uid = userids[x]
            mrank = 3
            mtableRanking = 3
            moWin.setResult('seat' + str(x + 1), [detalChips[x], seat_coin[x], 0, 0, 0, 0, mrank, mtableRanking])
             
            #增加经验
            exp = userdata.incrExp(uid, 20)
            explevel = dizhuaccount.getExpLevel(exp)
            gamedata.setGameAttr(uid, table.gameId, 'level', explevel)
            ftlog.debug('BigMatch.doWinLoseTable add 20 exp, tootle', exp, 'level', explevel)
             
#         nhWin = []
#         table.makeBroadCastUsers(nhWin)
#         tasklet.sendUdpToMainServer(moWin, nhWin)
        table.gamePlay.sender.sendToAllTableUser(moWin)
         
        # 发送给match manager
        users = []
        for x in xrange(len(userids)):
            user = {}
            user['userId'] = userids[x]
            user['deltaScore'] = int(detalChips[x])
            user['seatId'] = x + 1
            users.append(user)
         
        mnr_msg = MsgPack()
        mnr_msg.setCmd('room')
        mnr_msg.setParam('action', 'm_winlose')
        mnr_msg.setParam('gameId', table.gameId)
        mnr_msg.setParam('matchId', table.room.bigmatchId)
        mnr_msg.setParam('roomId', table.room.ctrlRoomId)
        mnr_msg.setParam('tableId', table.tableId)
        mnr_msg.setParam('users', users)
        mnr_msg.setParam('ccrc', table._match_table_info['ccrc'])
            
        if cls.WINLOSE_SLEEP > 0:
            FTTasklet.getCurrentFTTasklet().sleepNb(cls.WINLOSE_SLEEP)
        # 记录游戏winlose
        try:
            for u in users:
                table.room.reportBiGameEvent("TABLE_WIN", u['userId'], table.roomId, table.tableId, roundId, u['deltaScore'], 0, 0, [], 'table_win')
#                 cls.report_bi_game_event(TyContext.BIEventId.TABLE_WIN, u['userId'], table._rid, table._id, table._roundId, u['deltaScore'], 0, 0, [], 'table_win')                
        except:
            if ftlog.is_debug():
                ftlog.exception()
        router.sendRoomServer(mnr_msg, table.room.ctrlRoomId)
        
    @classmethod
    def _handleSigninException(cls, room, ex, uid, mo):
        msg = runcmd.getMsgPack()
        ddzver = msg.getParam('ddzver', 0) if msg else 0
        if ddzver < 3.772:
            infoTodotask = TodoTaskShowInfo(ex.message)
            mo = TodoTaskHelper.makeTodoTaskMsg(room.gameId, uid, infoTodotask)
            router.sendToUser(mo, uid)
        else:
            cls.sendDizhuFailureMsg(room.gameId, uid, '报名失败', ex.message, None)

    @classmethod
    def _handleSigninFeeNotEnoughException(cls, room, ex, uid, mo):
        payOrder = ex.fee.getParam('payOrder')
        clientId = sessiondata.getClientId(uid)
        clientOs, _clientVer, _ = strutil.parseClientId(clientId)
        msg = runcmd.getMsgPack()
        ddzver = msg.getParam('ddzver', 0) if msg else 0

        if ddzver >= 3.772:
            cls._handleSigninFeeNotEnoughException_V3_772(room, ex, uid, mo)
            return

        if payOrder:
            clientOs = clientOs.lower()
            product, _shelves = hallstore.findProductByPayOrder(room.gameId, uid, clientId, payOrder)
            if product:
                buyType = ''
                btnTxt = ''
                if ex.fee.assetKindId == hallitem.ASSET_CHIP_KIND_ID and clientOs == 'winpc':
                    user_diamond = userdata.getAttrInt(uid, 'diamond')
                    if user_diamond >= int(product.priceDiamond):
                        buyType = 'consume'
                        btnTxt = '兑换'
                    else:
                        buyType = 'charge'
                        btnTxt = '去充值'
                orderShow = TodoTaskOrderShow.makeByProduct(ex.fee.failure, '', product, buyType)
                orderShow.setParam('sub_action_btn_text', btnTxt)
                mo = TodoTaskHelper.makeTodoTaskMsg(room.gameId, uid, orderShow)
                router.sendToUser(mo, uid)
                return True
        mo = TodoTaskHelper.makeTodoTaskMsg(room.gameId, uid, TodoTaskShowInfo(ex.fee.failure))
        router.sendToUser(mo, uid)


    @classmethod
    def _handleSigninFeeNotEnoughException_V3_772(cls, room, ex, uid, mo):
        payOrder = ex.fee.getParam('payOrder')
        clientId = sessiondata.getClientId(uid)
        ftlog.debug("arenamatch._handleSigninFeeNotEnoughException_V3_772", "userId", uid, "fee.itemId=", ex.fee.assetKindId, "fee.params=", ex.fee.params)
        ftlog.debug("arenamatch._handleSigninFeeNotEnoughException_V3_772, userId=", uid, "payOrder=", payOrder)

        if payOrder:
            product, _shelves = hallstore.findProductByPayOrder(room.gameId, uid, clientId, payOrder)
            if not product:
                cls.sendDizhuFailureMsg(room.gameId, uid, '报名失败', ex.fee.failure, None)
                return

            buyType = ''
            btnTxt = ''
            if ex.fee.assetKindId == hallitem.ASSET_CHIP_KIND_ID: # 金币是报名费
                orderShow = TodoTaskOrderShow.makeByProduct(ex.fee.failure, '', product, buyType)
                orderShow.setParam('sub_action_btn_text', btnTxt)
                mo = TodoTaskHelper.makeTodoTaskMsg(room.gameId, uid, orderShow)
                router.sendToUser(mo, uid)
                return

        ## 其他报名费/gotoshop
        todotask = ex.fee.getParam('todotask')
        todoTaskObj = None
        ftlog.debug("arenamatch._handleSigninFeeNotEnoughException_V3_772, userId=", uid, "todotask=", todotask)
        if todotask:
            todoTaskObj = hallpopwnd.decodeTodotaskFactoryByDict(todotask).newTodoTask(room.gameId, uid, clientId)
        cls.sendDizhuFailureMsg(room.gameId, uid, '报名失败', ex.fee.failure, todoTaskObj, '去商城')


    @classmethod
    def sendDizhuFailureMsg(cls, gameId, userId, title, message, todotask=None, buttonTitle=None):
        Alert.sendNormalAlert(gameId, userId, title, message, todotask, buttonTitle)


