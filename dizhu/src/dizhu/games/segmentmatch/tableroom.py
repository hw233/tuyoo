# -*- coding:utf-8 -*-
'''
Created on 2018年4月13日

@author: wangyonghui
'''
from dizhu.games.normalbase.tableroom import DizhuPlayerNormalBase, DizhuTableRoomNormalBase
from dizhu.games.segmentmatch import dealer
from dizhu.games.segmentmatch.policies import AssignTableWinStreakPolicy
from dizhu.games.segmentmatch.table import DizhuTableCtrlSegmentMatch
from dizhu.servers.util.rpc import new_table_remote
from dizhucomm.core.const import StandupReason
from poker.entity.game.rooms.room import TYRoom
import freetime.util.log as ftlog


class DizhuPlayerSegmentMatch(DizhuPlayerNormalBase):
    def __init__(self, room, userId):
        super(DizhuPlayerSegmentMatch, self).__init__(room, userId)
        self.segment = 0
        self.currentStar = 0

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

    def isFirstWin(self, isWin):
        if not isWin:
            return False
        import poker.util.timestamp as pktimestamp
        today = pktimestamp.formatTimeDayInt()
        isFirstWin = self._datas.get('firstWin', {}).get(str(today), 0)
        if not isFirstWin:
            return True
        return False



class DizhuTableRoomSegmentMatch(DizhuTableRoomNormalBase):
    def __init__(self, roomDefine):
        super(DizhuTableRoomSegmentMatch, self).__init__(roomDefine)
        self._dealer = dealer.DIZHU_DEALER_DICT[self.roomConf['playMode']]
        self._joinSegmentPolicy = AssignTableWinStreakPolicy()

    def newTable(self, tableId):
        tableCtrl = self._makeTableCtrl(tableId, self._dealer)
        tableCtrl.setupTable()
        self._addTable(tableCtrl.table)
        self._joinSegmentPolicy.setupTable(tableCtrl.table)
        return tableCtrl

    def _enterRoomCheck(self, player, continueBuyin):
        pass

    def _makeTableCtrl(self, tableId, myDealer):
        return DizhuTableCtrlSegmentMatch(self, tableId, myDealer)

    def _makePlayer(self, userId):
        return DizhuPlayerSegmentMatch(self, userId)

    def enterRoom(self, userId, continueBuyin):
        '''
        用户进入房间，带入，取用户信息等
        '''
        with self._keyLock.lock(userId):

            exists = self.findPlayer(userId)
            if exists:
                ftlog.info('DizhuPlayerSegmentMatch.enterRoom',
                           'userId=', userId,
                           'clientId=', exists.clientId,
                           'dizhuVersion=', exists.gameClientVer,
                           'idlePlayerCount=', len(self._idlePlayerMap),
                           'playerCount=', len(self._playerMap),
                           'tableCount=', len(self._tableList),
                           'continueBuyin=', True,
                           'roomId=', self.roomId)
                return exists

            player = self._makePlayer(userId)
            player.initPlayer()

            # 检查准入
            self._enterRoomCheck(player, continueBuyin)

            self.ensureNotInSeat(userId)

            self._addPlayer(player)
            ftlog.info('DizhuPlayerSegmentMatch.enterRoom',
                       'userId=', userId,
                       'clientId=', player.clientId,
                       'dizhuVersion=', player.gameClientVer,
                       'idlePlayerCount=', len(self._idlePlayerMap),
                       'playerCount=', len(self._playerMap),
                       'tableCount=', len(self._tableList),
                       'continueBuyin=', continueBuyin,
                       'segment=', player.segment,
                       'roomId=', self.roomId)
            return player

    def leaveRoom(self, userId, reason):
        '''
        玩家离开房间
        '''
        with self._keyLock.lock(userId):
            player = self.findPlayer(userId)


            if ftlog.is_debug():
                ftlog.debug('DizhuPlayerSegmentMatch.leaveRoom',
                            'roomId=', self.roomId,
                            'userId=', userId,
                            'player=', player,
                            'reason=', reason,
                            'tableId=', player.tableId if player else None,
                            'seatId=', player.seatId if player else None,
                            'tableState=', (player.table.state.name if player.table else None) if player else None)

            ret = True
            if player:
                # 断线不离开房间（防止用户网不好导致连胜中断）
                if reason == TYRoom.LEAVE_ROOM_REASON_LOST_CONNECTION:
                    if not player.table:
                        player.online = False
                        return False
                    if player.table.gameRound:
                        player.table.offline(player.seat)
                        return False
                    else:
                        return player.table.standup(player.seat, StandupReason.TCP_CLOSED)

                if player.seat:
                    ret = player.table.standup(player.seat)
                if not player.seat:
                    self._leaveRoom(player, reason)
            return ret

    def _getTable(self, player):
        '''
        查找一张合适的桌子
        '''
        found = None
        if ftlog.is_debug():
            ftlog.debug('DizhuPlayerSegmentMatch._getTable',
                        'roomId=', self.roomId,
                        'userId=', player.userId,
                        'tableCount=', len(self._tableList))

        candidateList = []
        for table in self._tableList:
            if table.processing:
                continue
            idleSeatCount = table.idleSeatCount
            if idleSeatCount <= 0:
                break
            if table.state.name != 'idle':
                if ftlog.is_debug():
                    ftlog.debug('DizhuPlayerSegmentMatch._getTable BadTableState',
                                'roomId=', self.roomId,
                                'userId=', player.userId,
                                'tableId=', table.tableId,
                                'tableState=', table.state.name,
                                'idleSeatCount=', idleSeatCount)
                continue
            if idleSeatCount == table.seatCount:
                found = table
                break
            else:
                if (self._joinTablePolicy
                        and not self._joinTablePolicy.canJoin(table, player)):
                    continue
                candidateList.append(table)

                # 段位匹配规则
                if self._joinSegmentPolicy.canJoin(table, player):
                    found = table
                    break
                # else:
                #     found = table
                #     break

        if not found and candidateList:
            found = candidateList[0]
            if ftlog.is_debug():
                ftlog.debug('DizhuPlayerSegmentMatch._getTable',
                            'roomId=', self.roomId,
                            'userId=', player.userId,
                            'candidateList=', [t.tableId for t in candidateList])
        if not found:
            ftlog.warn('DizhuPlayerSegmentMatch._getTable',
                       'roomId=', self.roomId,
                       'userId=', player.userId,
                       'table=', None)
        return found
