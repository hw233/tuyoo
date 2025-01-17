# -*- coding:utf-8 -*-
'''
Created on 2017年6月13日

@author: wangyonghui
'''
from dizhu.games.mix import dealer
from dizhu.games.mix.policies import AssignTableWithMixIdPolicy
from dizhu.games.mix.table import DizhuTableCtrlMix
from dizhu.games.mix.tabletask import WinStreakTaskSystemMix
from dizhu.games.normalbase.tableroom import DizhuPlayerNormalBase, \
    DizhuTableRoomNormalBase
from dizhu.servers.util.rpc import new_table_remote
from dizhucomm.core.exceptions import ChipNotEnoughException
import freetime.util.log as ftlog
from dizhucomm.room.events import RoomConfReloadEvent
from freetime.entity.msg import MsgPack
from poker.entity.game.rooms.room import TYRoom
from poker.protocol import router


class DizhuPlayerMix(DizhuPlayerNormalBase):
    def __init__(self, room, userId, mixId):
        super(DizhuPlayerMix, self).__init__(room, userId)
        self.mixId = mixId
        self.mixConf = {}
        self.segment = 0
        self.currentStar = 0

    def reloadMixConf(self):
        if self.mixId:
            for mixConf in self.room.roomConf.get('mixConf', []):
                if mixConf.get('mixId') == self.mixId:
                    self.mixConf = mixConf

    def initPlayer(self):
        '''
        填充player信息
        '''
        if self.needInit:
            self.needInit = False
            datas = new_table_remote.doInitTablePlayerDatas(self.userId, self.room.roomId, mixConf=self.mixConf)
            self.updateDatas(datas)
        return self

    def updateDatas(self, datas):
        self._datas = datas
        self.clientId = datas.get('clientId', '')
        self.name = datas.get('name', '')
        self.chip = datas.get('chip', 0)
        self.gameClientVer = datas.get('gameClientVer', 0)

        segment, currentStar = new_table_remote.doGetUserSegment(self.userId)
        self.segment = segment
        self.currentStar = currentStar
        self.updateSegmentDatas()


    def updateSegmentDatas(self):
        self._datas.update({'segment': self.segment, 'currentStar': self.currentStar})

    def isFirstLose(self, isWin):
        if isWin:
            return False
        if self._datas['registerDays'] < 3:
            wins = self._datas.get('winrate2', {}).get('wt', 0)
            plays = self._datas.get('winrate2', {}).get('pt', 0)
            return wins == plays

    def isFirstWin(self, isWin):
        if not isWin:
            return False
        import poker.util.timestamp as pktimestamp
        today = pktimestamp.formatTimeDayInt()
        isFirstWin = self._datas.get('firstWin', {}).get(str(today), 0)
        if not isFirstWin:
            return True
        return False


class DizhuTableRoomMix(DizhuTableRoomNormalBase):
    def __init__(self, roomDefine):
        super(DizhuTableRoomMix, self).__init__(roomDefine)
        self._dealer = dealer.DIZHU_DEALER_DICT[self.roomConf['playMode']]
        self._winStreakTask = WinStreakTaskSystemMix(self)
        self._assignTableWithMixIdPolicy = AssignTableWithMixIdPolicy()
        self.on(RoomConfReloadEvent, self._onRoomConfReload)

    def _onRoomConfReload(self, event):
        for userId, player in self._playerMap.items():
            player.reloadMixConf()

        if ftlog.is_debug():
            ftlog.debug('DizhuTableRoomMix._onRoomConfReload roomId=', self.roomId)

    def quickStart(self, userId, tableId, continueBuyin, mixId=''):
        if ftlog.is_debug():
            ftlog.debug('DizhuTableRoomMix.quickStart',
                        'userId=', userId,
                        'roomId=', self.roomId,
                        'tableId=', tableId,
                        'continueBuyin=', continueBuyin,
                        'mixId=', mixId)
        if tableId:
            player = self.findPlayer(userId)
            if player:
                if player.table:
                    player.table.online(player.seat)
                    return player
                player.online = True

        # 开始游戏
        try:
            player = self.enterRoom(userId, continueBuyin, mixId)
            seat = self.startGame(userId, continueBuyin)
        except Exception, e:
            self.leaveRoom(userId, TYRoom.LEAVE_ROOM_REASON_LESS_MIN)
            ftlog.warn('DizhuTableRoomNormalBase.quickStart'
                       'userId=', userId,
                       'roomId=', self.roomId,
                       'continueBuyin=', continueBuyin,
                       'warn=', e.message)
            # 发送离开房间
            mp = MsgPack()
            mp.setCmd('room_leave')
            mp.setResult('reason', 0)
            mp.setResult('gameId', self.gameId)
            mp.setResult('roomId', self.roomId)  # 处理结果返回给客户端时，部分游戏（例如德州、三顺）需要判断返回的roomId是否与本地一致
            mp.setResult('userId', userId)
            router.sendToUser(mp, userId)
            return
        return seat

    def enterRoom(self, userId, continueBuyin, mixId=''):
        '''
        用户进入房间，带入，取用户信息等
        '''
        with self._keyLock.lock(userId):
            exists = self.findPlayer(userId)
            if exists:
                if mixId:
                    mixConf = exists.mixConf
                    if mixConf.get('mixId') != mixId:
                        # 清空所有连胜任务
                        playerTask = self._winStreakTask.getPlayerTask(exists)
                        if playerTask:
                            playerTask._reward = None
                            playerTask._progress = 0
                        exists.mixId = mixId
                        exists.reloadMixConf()
                exists.continueBuyin = True
                return exists

            player = self._makePlayer(userId, mixId)
            player.reloadMixConf()
            player.initPlayer()

            # 检查准入
            self._enterRoomCheck(player, continueBuyin, mixId)

            self.ensureNotInSeat(userId)

            self._addPlayer(player)
            ftlog.info('DizhuTableRoomMix.enterRoom',
                       'userId=', userId,
                       'mixId=', mixId,
                       'mixConf=', player.mixConf,
                       'continueBuyin=', continueBuyin,
                       'roomId=', self.roomId)
            return player

    def _enterRoomCheck(self, player, continueBuyin, mixId=''):
        '''
        检查用户是否可以进入该房间
        '''

        # 兼容老版本
        gameClientVer = player.gameClientVer
        if continueBuyin and gameClientVer < 3.818:
            if ftlog.is_debug():
                ftlog.debug('DizhuTableRoomMix._enterRoomCheck',
                            'userId=', player.userId,
                            'roomId=', self.roomId,
                            'mixId=', mixId,
                            'continueBuyin=', continueBuyin,
                            'gameClientVer=', gameClientVer)

            kickOutCoin = player.mixConf.get('kickOutCoin', 0)
            if player.chip < kickOutCoin:
                raise ChipNotEnoughException()
            return

        # 检查location
        roomMinCoin = player.mixConf.get('minCoin', 0)
        if player.chip < roomMinCoin:
            raise ChipNotEnoughException()

    def _makeTableCtrl(self, tableId, dealer):
        return DizhuTableCtrlMix(self, tableId, dealer)

    def _makePlayer(self, userId, mixId=''):
        return DizhuPlayerMix(self, userId, mixId)

