# -*- coding:utf-8 -*-
'''
Created on 2017年2月18日

@author: zhaojiangang
'''
from dizhu.entity.dizhu_friend import FriendHelper
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.games.friend.event import FTDisbindEvent, FTContinueEvent, \
    FTContinueErrorEvent
from dizhu.games.tablecommonproto import DizhuTableProtoCommonBase
import freetime.util.log as ftlog
from dizhu.servers.util.rpc import new_table_remote
from poker.entity.biz.content import TYContentItem
from poker.entity.configure import pokerconf
from poker.protocol import router
from poker.util import timestamp as pktimestamp


class FTLeaveReason(object):
    CREATOR_DISBAND = 10001 # 房主解散房间 （整牌局未开始，房主可以直接解散牌桌）
    ALL_DISBAND     = 10002 # 投票解散了 （好友桌过程中，必须所有人投票决定解散牌桌）
    GAME_OVER       = 10003 # 结束了 （所有牌局打完，房主没有续桌）
    INITIATE_QUIT   = 10004 # 主动退出 （整牌局未开始，玩家（非房主）可以直接离开房间））
    NOT_START       = 10005 # 时间到了还未开始游戏 （好友桌开始前，一定时间内还未开始游戏，强制解散）
    SYSTEM_TIME_OUT = 10006 # 系统规定时间到了 （整个牌局有一个限制时间，到时间没有打完）

class FTTableDetails(object):
    def __init__(self):
        self.ftId = None
        self.userId = None
        self.nRound = None
        self.fee = None
        self.canDouble = None
        self.playMode = None
        self.expires = None
        self.goodCard = None
        
    def fromDict(self, d):
        self.ftId = d['ftId']
        fee = d.get('fee')
        if fee:
            self.fee = TYContentItem.decodeFromDict(d['fee'])
        self.userId = d['userId']
        self.nRound = d['nRound']
        self.canDouble = d['canDouble']
        self.playMode = d['playMode']
        self.expires = d['expires']
        self.goodCard = d['goodCard']
        return self

class DizhuTableProtoFriend(DizhuTableProtoCommonBase):
    def __init__(self, tableCtrl):
        super(DizhuTableProtoFriend, self).__init__(tableCtrl)
    
    def setupTable(self):
        super(DizhuTableProtoFriend, self).setupTable()
        self.table.on(FTDisbindEvent, self._onDisbindFT)
        self.table.on(FTContinueEvent, self._onContinueFT)
        self.table.on(FTContinueErrorEvent, self._onContinueErrorFT)
        
    # 好友桌重写QuickStart消息
    def buildQuickStartResp(self, seat, isOK, reason):
        mp = self.buildTableMsgRes('quick_start')
        mp.setResult('isOK', isOK)
        mp.setResult('seatId', seat.seatId)
        mp.setResult('reason', reason)
        mp.setResult('tableType', 'friend')
        return mp

    def sendTableInfoRes(self, seat):
        logUserIds = [66706022]
        if seat.player and seat.userId in logUserIds:
            ftlog.info('DizhuTableProtoFriend.sendTableInfoRes beforeSentMsg',
                       'tableId=', self.tableId,
                       'userId=', seat.userId,
                       'gameClientVer=', seat.player.gameClientVer,
                       'isGiveup=', seat.isGiveup,
                       'isQuit=', seat.player.isQuit,
                       'seats=', [(s.userId, s.seatId) for s in self.table.seats])

        if seat.player and not seat.isGiveup and not seat.player.isQuit:
            mp = self.buildTableInfoResp(seat, 0)
            router.sendToUser(mp, seat.userId)
            if seat.userId in logUserIds:
                ftlog.info('DizhuTableProtoFriend.sendTableInfoRes sentMsg',
                           'tableId=', self.tableId,
                           'userId=', seat.userId,
                           'gameClientVer=', seat.player.gameClientVer,
                           'seats=', [(seat.userId, seat.seatId) for seat in self.table.seats],
                           'mp=', mp.pack())

    # 好友桌重写TableInfo消息
    def buildTableInfoResp(self, seat, isRobot):
        mp = super(DizhuTableProtoFriend, self).buildTableInfoResp(seat, isRobot)
        if self.tableCtrl._preDisbind:
            mp.setResult('disbind', {
                'reqSeatId':self.tableCtrl._preDisbindSeat.seatId,
                'states':self.tableCtrl._preDisbindSeatState[:],
                'optime':max(0, self.tableCtrl._preDisbindExpires - pktimestamp.getCurrentTimestamp())
            })
        mp.setResult('ftInfo', self.buildFTInfo())
        mp.setResult('results', self.tableCtrl.results or [])
        dailyPlayCount = new_table_remote.doGetUserDailyPlayCount(seat.userId, DIZHU_GAMEID)
        mp.setResult('dailyPlay', dailyPlayCount)
        return mp
    
    def buildUserReadyRes(self, seat):
        mp = super(DizhuTableProtoFriend, self).buildUserReadyRes(seat)
        mp.setResult('mscore', seat.player.score)
        seats = []
        for seat in self.table.seats:
            if seat.player and not seat.isGiveup:
                seats.append(seat.player.score)
            else:
                seats.append(0)
        mp.setResult('seats', seats)
        return mp
    
    def buildGameReadyRes(self, seat):
        mp = super(DizhuTableProtoFriend, self).buildGameReadyRes(seat)
        mp.setResult('ftInfo', self.buildFTInfo())
        return mp
    
    def buildFTInfo(self):
        curRound = self.tableCtrl.nRound
        if self.tableCtrl.table.gameRound:
            curRound += 1
        ret = {
            'ftId':self.tableCtrl.ftTable.ftId,
            'creator':self.tableCtrl.ftTable.userId,
            'curRound':curRound,
            'playMode':self.tableCtrl.ftTable.playMode,
            'totalRound':self.tableCtrl.ftTable.nRound,
            'double':self.tableCtrl.ftTable.canDouble,
            'goodCard':self.tableCtrl.ftTable.goodCard,
            'fee':self.tableCtrl.ftTable.fee.count if self.tableCtrl.ftTable.fee else 0
        }
        return ret
    
    def buildWinloseResults(self):
        if not self.tableCtrl.lastResult:
            return self.tableCtrl.results
        ret = self.tableCtrl.results[:]
        ret.append(self.tableCtrl.lastResult)
        return ret
    
    def buildWinloseAbortRes(self, result):
        mp = super(DizhuTableProtoFriend, self).buildWinloseAbortRes(result)
        mp.setResult('ftId', self.tableCtrl.ftTable.ftId)
        curRound = self.tableCtrl.nRound
        mp.setResult('curRound', curRound)
        mp.setResult('totalRound', self.tableCtrl.ftTable.nRound)
        mp.setResult('results', self.buildWinloseResults())
        if self.tableCtrl.isFinished:
            mp.setResult('finish', 1)
        statics = self.tableCtrl.staticsResults()
        if statics:
            mp.setResult('statics', statics)
        return mp
    
    def buildResultDetails(self, result):
        luckyItemArgs = []
        winStreak = []
        skillScoreInfos = []
        cards = []
        addCoupons = []
        seatDetails = []
        seatInfos = []
        tableTasks = []
        for sst in result.seatStatements:
            waittime = self.table.runConf.optimeCall
            if sst.final < self.table.runConf.minCoin:
                waittime = int(waittime/3)
            details = [
                sst.delta,
                sst.final,
                0,
                waittime,
                0,
                0,
                sst.expInfo[0], sst.expInfo[1], sst.expInfo[2], sst.expInfo[3], sst.expInfo[4],
                sst.final
            ]
            seatDetails.append(details)
            luckyItemArgs.append({})
            winStreak.append(sst.winStreak)
            skillScoreInfos.append(sst.skillscoreInfo)
            cards.append(sst.seat.status.cards)
            addCoupons.append(0)
            tableTasks.append([])
            seatInfos.append({'punished': 1} if sst.isPunish else {})
        
        return {
            'winStreak':winStreak,
            'luckyItemArgs':luckyItemArgs,
            'skillScoreInfos':skillScoreInfos,
            'addcoupons':addCoupons,
            'cards':cards,
            'seatDetails':seatDetails,
            'seatInfos':seatInfos,
            'tableTasks':tableTasks
        }

    def buildWinloseRes(self, result, details, save):
        mp = super(DizhuTableProtoFriend, self).buildWinloseRes(result, details, 0)
        mp.setResult('ftId', self.tableCtrl.ftTable.ftId)
        curRound = self.tableCtrl.nRound
        mp.setResult('curRound', curRound)
        mp.setResult('totalRound', self.tableCtrl.ftTable.nRound)
        mp.setResult('results', self.tableCtrl.results)
        if self.tableCtrl.isFinished:
            mp.setResult('finish', 1)
        statics = self.tableCtrl.staticsResults()
        if statics:
            mp.setResult('statics', statics)
        return mp
    
    def sendRoomLeaveAll(self, reason, returnFee=False):
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend.sendRoomLeaveAll:',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftTable.ftId)
        for seat in self.table.seats:
            self.sendRoomLeave(seat, reason, returnFee)

    def sendRoomLeave(self, seat, reason, returnFee=False):
        if not seat.player:
            return 
        if not pokerconf.isOpenMoreTable(seat.player.clientId) :
            mo = self.buildTableMsgRes('room_leave')
        else:
            mo = self.buildTableMsgRes('room', 'leave')
        mo.setResult('reason', reason)
        mo.setResult('returnFee', 1 if returnFee else 0)
        mo.setResult('userId', seat.userId)
        self.sendToSeat(mo, seat)
    
    def sendReqDisbindAll(self, reqSeat):
        '''
        向牌桌上的所有玩家发送请求解散
        @param reqSeat: 发起者 
        '''
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend.sendReqDisbindAll:',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftTable.ftId,
                        'userId=', reqSeat.userId,
                        'seatId=', reqSeat.seatId)
        mo = self.buildTableMsgRes('table_call', 'ft_req_disbind')
        mo.setResult('seatId', reqSeat.seatId)
        mo.setResult('userId', reqSeat.userId)
        optime = self.table.runConf.optimeDisbind
        mo.setResult('optime', optime)
        mo.setResult('disbinds', self.tableCtrl._preDisbindSeatState[:])
        self.sendToAllSeat(mo)
    
    def sendDisbindAll(self):
        '''
        发送解散消息
        '''
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend.sendDisbindAll:',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftId)
        statics = self.tableCtrl.staticsResults()
        if ftlog.is_debug():
            ftlog.debug('DizhuFTSender.sendDisbindRes',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftTable.ftId)
        mp = self.buildTableMsgRes('table_call', 'ft_disbind')
        mp.setResult('ftId', self.tableCtrl.ftTable.ftId)
        mp.setResult('results', self.tableCtrl.results)
        if statics:
            mp.setResult('statics', statics)
        self.sendToAllSeat(mp)
        
    def sendReqDisbindAnswerResAll(self, seat, disbinds):
        '''
        发送 解散请求 玩家回复结果
        '''
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend.sendReqDisbindAnswerResAll:',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftTable.ftId,
                        'userId=', seat.userId,
                        'seatId=', seat.seatId,
                        'disbinds=', disbinds)
        mp = self.buildTableMsgRes('table_call', 'ft_req_disbind_answer')
        mp.setResult('ftId', self.tableCtrl.ftTable.ftId)
        mp.setResult('seatId', seat.seatId)
        mp.setResult('userId', seat.userId)
        mp.setResult('disbinds', disbinds)
        self.sendToAllSeat(mp)
        
    def sendReqDisbindResultResAll(self, disbinds, disbindResult):
        '''
        发送 解散请求 最终结果
        '''
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend.sendReqDisbindResultResAll',
                        'tableId=', self.table.tableId,
                        'ftId=', self.tableCtrl.ftTable.ftId,
                        'disbinds=', disbinds,
                        'disbindResult=', disbindResult)
        mo = self.buildTableMsgRes('table_call', 'ft_req_disbind_result')
        mo.setResult('disbinds', disbinds)
        mo.setResult('disbindResult', disbindResult)
        self.sendToAllSeat(mo)
    
    def _onDisbindFT(self, event):
        '''
        处理解散事件
        '''
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend._onDisbindFT',
                        'tableId=', event.table.tableId)
        self.sendDisbindAll()
        self.sendRoomLeaveAll(event.reason, event.returnFee)
        
    def _onContinueFT(self, event):
        '''
        发送继续成功的消息
        '''
        mp = self.buildTableMsgRes('table_call', 'ft_continue')
        mp.setResult('seatId', event.seat.seatId)
        mp.setResult('userId', event.seat.userId)
        mp.setResult('code', 0)
        self.sendToSeat(mp, event.seat)
    
    def _onContinueErrorFT(self, event):
        '''
        发送继续错误的消息
        '''
        mp = self.buildTableMsgRes('table_call', 'ft_continue')
        mp.setResult('seatId', event.seat.seatId)
        mp.setResult('userId', event.seat.userId)
        mp.setResult('code', event.ec)
        mp.setResult('info', event.errmsg)
        self.sendToSeat(mp, event.seat)
    
    def _onContinueTimeoutFT(self, event):
        '''
        结算界面时间到了还没继续，发送离开牌桌的消息
        '''
        self.sendRoomLeaveAll(FTLeaveReason.GAME_OVER)
        
    def _onGameReady(self, event):
        super(DizhuTableProtoFriend, self)._onGameReady(event)
        # 取消未开始直接解散牌桌计时器
        if self.tableCtrl._notStartTimer:
            self.tableCtrl._notStartTimer.cancel()
            self.tableCtrl._notStartTimer = None

    def _do_table_manage__ft_bind(self, msg):
        '''
        绑定牌桌
        '''
        ftlog.debug('DizhuTableProtoFriend._do_table_manage__ft_bind:',
                    'msg=', msg)
        ftTable = FTTableDetails().fromDict(msg.getParam('ftTable'))
        self.tableCtrl.bindFT(ftTable)

    def _do_table_call__ft_req_disbind(self, msg):
        '''
        解散请求
        '''
        ftlog.debug('DizhuTableProtoFriend._do_table_manage__ft_req_disbind:',
                    'msg=', msg)
        userId = msg.getParam('userId')
        seatId = msg.getParam('seatId')
        self.tableCtrl.reqDisbind(userId, seatId)

    def _do_table_call__ft_req_disbind_answer(self, msg):
        '''
        解散请求
        '''
        ftlog.debug('DizhuTableProtoFriend._do_table_call__ft_req_disbind_answer:',
                    'msg=', msg)
        userId = msg.getParam('userId')
        seatId = msg.getParam('seatId')
        answer = msg.getParam('answer')
        self.tableCtrl.reqDisbindAnswer(userId, seatId, answer)

    def _do_table_call__ft_continue(self, msg):
        '''
        续桌请求
        '''
        ftlog.debug('DizhuTableProtoFriend._do_table_call__ft_continue:',
                    'msg=', msg)
        userId = msg.getParam('userId')
        seatId = msg.getParam('seatId')
        self.tableCtrl.continueFT(userId, seatId)

    def _do_table_call__ft_req_invite(self, msg):
        '''
        微信邀请
        '''
        userId = msg.getParam('userId')
        seatId = msg.getParam('seatId')
        ftlog.info('DizhuTableProtoFriend._do_table_call__ft_req_invite',
                   'userId=', userId,
                   'tableId=', self.table.tableId,
                   'ftId=', self.tableCtrl.ftTable.ftId if self.tableCtrl.ftTable else None)
        self.tableCtrl.inviteFriend(userId, seatId)

    def _onGameStart(self, event):
        super(DizhuTableProtoFriend, self)._onGameStart(event)
        userIds = [s.player.userId for s in event.table.seats]
        from dizhu.game import TGDizhu
        from dizhu.entity.common.events import ActiveEvent
        for userId in userIds:
            TGDizhu.getEventBus().publishEvent(ActiveEvent(6, userId, 'friendGame'))
        # 朋友桌第一局启动， 默认加好有
        if ftlog.is_debug():
            ftlog.debug('DizhuTableProtoFriend._onGameStart',
                        'tableId=', self.table.tableId,
                        'userIds=', userIds,
                        'nRound=', self.tableCtrl.nRound,
                        )
        if self.tableCtrl.nRound == 0:
            for seat in event.table.seats:
                # 加好友, 转到UT服执行
                new_table_remote.addWechatFriend(seat.player.userId, userIds)
