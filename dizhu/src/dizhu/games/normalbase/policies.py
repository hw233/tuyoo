# -*- coding:utf-8 -*-
'''
Created on 2017年2月14日

@author: zhaojiangang
'''
import random
import time

from dizhucomm.core.events import SitdownEvent, StandupEvent
from dizhucomm.core.policies import FirstCallPolicy, FirstCallPolicyRandom
import freetime.util.log as ftlog


class AssignTableWinStreakPolicy(object):
    def setupTable(self, table):
        table.winStreakSection = None
        table.on(SitdownEvent, self._onSitdownEvent)
        table.on(StandupEvent, self._onStandupEvent)
        
    def getPlayerWinStreak(self, table, player):
        playerTask = table.room.winStreakTask.getPlayerTask(player)
        return playerTask.progress if playerTask else 0
    
    def getWinStreakSection(self, table, winStreak):
        winStreakAssignTableConf = None
        try:
            winStreakAssignTableConf = self.getWinStreakAssignTableConf(table)
            if winStreakAssignTableConf:
                for section in winStreakAssignTableConf.get('sections', []):
                    if winStreak >= section[0] and winStreak <= section[1]:
                        if ftlog.is_debug():
                            ftlog.debug('AssignTableWinStreakPolicy.getWinStreakSection',
                                        'tableId=', table.tableId,
                                        'winStreak=', winStreak,
                                        'section=', section,
                                        'winStreakAssignTableConf=', winStreakAssignTableConf)
                        return section
            return None
        except:
            ftlog.error('AssignTableWinStreakPolicy.getWinStreakSection',
                        'tableId=', table.tableId,
                        'winStreakAssignTableConf=', winStreakAssignTableConf)
            return None
    
    def getWinStreakAssignTableConf(self, table):
        return table.runConf.datas.get('winStreakAssignTable')
    
    def getTimeoutThreshold(self, table):
        winStreakAssignTableConf = self.getWinStreakAssignTableConf(table)
        if not winStreakAssignTableConf:
            return 0
        return winStreakAssignTableConf.get('timeout', -1)
    
    def canJoin(self, table, player):
        # 空桌子可以坐下
        if table.idleSeatCount == table.seatCount:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin EmptyTable',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True
        
        # 如果房间没有配置连胜则可以坐下
        taskList = table.room.winStreakTask.taskList
        if not taskList:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin EmptyWinStreakTask',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True
        
        # 获取连胜区间
        if not table.winStreakSection:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin EmptyTableWinStreakSection',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True
        
        # 玩家连胜在该桌子的连胜区间内
        winStreak = self.getPlayerWinStreak(table, player)
        if (winStreak >= table.winStreakSection[0]
            and winStreak <= table.winStreakSection[1]):
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin InTableWinStreakSection',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'winStreak=', winStreak,
                            'tableWinStreakSection=', table.winStreakSection,
                            'ret=', True)
            return True
        
        # 桌子等待时间超过阈值 -1 表示无限大
        timeoutThreshold = self.getTimeoutThreshold(table)
        if timeoutThreshold < 0:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin InfinityTimeout',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'timeoutThreshold=', timeoutThreshold,
                            'ret=', False)
            return False
        
        earliesPlayer = self._getEarliestSitdownPlayer(table)
        assert(earliesPlayer)
        
        nowTime = int(time.time())
        if nowTime - earliesPlayer.sitdownTime >= timeoutThreshold:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWinStreakPolicy.canJoin OverTimeout',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'timeoutThreshold=', timeoutThreshold,
                            'sitdownTime=', earliesPlayer.sitdownTime,
                            'nowTime=', nowTime,
                            'ret=', True)
            return True 
        
        return False
    
    def _getEarliestSitdownPlayer(self, table):
        ret = None
        for seat in table.seats:
            if not seat.player:
                continue
            if ret is None or seat.player.sitdownTime < ret.sitdownTime:
                ret = seat.player
        return ret
    
    def _onSitdownEvent(self, evt):
        evt.player.sitdownTime = int(time.time())
        winStreak = self.getPlayerWinStreak(evt.table, evt.player)
        evt.table.winStreakSection = self.getWinStreakSection(evt.table, winStreak)
        if ftlog.is_debug():
            ftlog.debug('AssignTableWinStreakPolicy._onSitdownEvent',
                        'seat=', (evt.player.userId, evt.player.seatId),
                        'winStreak=', winStreak,
                        'winStreakSeaction=', evt.table.winStreakSection)

    def _onStandupEvent(self, evt):
        if ftlog.is_debug():
            ftlog.debug('AssignTableWinStreakPolicy._onStandupEvent',
                        'seat=', (evt.player.userId, evt.seat.seatId))
        evt.player.sitdownTime = 0
        if evt.table.idleSeatCount == evt.table.seatCount:
            # 桌子没人了
            evt.table.winStreakSection = None


class AssignTableWithChipPolicy(object):
    '''
    已用户金币为基准的配桌策略
    '''
    def setupTable(self, table):
        table.chipSection = None
        table.on(SitdownEvent, self._onSitdownEvent)
        table.on(StandupEvent, self._onStandupEvent)

    def getPlayerChip(self, table, player):
        if not player.score:
            if table.room.roomConf.get('isMix'):
                # 混房
                return min(player.mixConf.get('buyinchip', 0), player.chip)
            else:
                return min(table.room.roomConf.get('buyinchip', 0), player.chip)
        return player.score

    def getChipSection(self, table, chip):
        '''
        获取配桌金币区间，用来赋值给桌子 chipSection 属性
        '''
        chipAssignTableConf = None
        try:
            chipAssignTableConf = self.getChipAssignTableConf(table)
            if chipAssignTableConf:
                for section in chipAssignTableConf.get('sections', []):
                    if (section[0] == -1 or chip >= section[0]) and (section[1] == -1 or chip <= section[1]):
                        if ftlog.is_debug():
                            ftlog.debug('AssignTableWithChipPolicy.getChipSection',
                                        'tableId=', table.tableId,
                                        'chip=', chip,
                                        'section=', section,
                                        'chipAssignTableConf=', chipAssignTableConf)
                        return section
            return None
        except:
            ftlog.error('AssignTableWithChipPolicy.getChipSection',
                        'tableId=', table.tableId,
                        'chipAssignTableConf=', chipAssignTableConf)
            return None

    def getChipAssignTableConf(self, table):
        return table.runConf.datas.get('chipAssignTable')

    def getTimeoutThreshold(self, table):
        chipAssignTableConf = self.getChipAssignTableConf(table)
        if not chipAssignTableConf:
            return 0
        return chipAssignTableConf.get('timeout', -1)

    def canJoin(self, table, player):
        # 空桌子可以坐下
        if table.idleSeatCount == table.seatCount:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithChipPolicy.canJoin EmptyTable',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True

        # 获取金币区间
        if not table.chipSection:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithChipPolicy.canJoin EmptyTableChipSection',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True
        # 玩家金币在该桌子的金币区间内
        chip = self.getPlayerChip(table, player)
        if (table.chipSection[0] == -1 or chip >= table.chipSection[0]) and (table.chipSection[1] == -1 or chip <= table.chipSection[1]):
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithChipPolicy.canJoin InTableChipSection',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'chip=', chip,
                            'tableChipSection=', table.chipSection,
                            'ret=', True)
            return True

        # 桌子等待时间超过阈值 -1 表示无限大
        timeoutThreshold = self.getTimeoutThreshold(table)
        if timeoutThreshold < 0:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithChipPolicy.canJoin InfinityTimeout',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'timeoutThreshold=', timeoutThreshold,
                            'ret=', False)
            return False

        earliesPlayer = self._getEarliestSitdownPlayer(table)
        assert (earliesPlayer)

        nowTime = int(time.time())
        if nowTime - earliesPlayer.sitdownTime >= timeoutThreshold:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithChipPolicy.canJoin OverTimeout',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'timeoutThreshold=', timeoutThreshold,
                            'sitdownTime=', earliesPlayer.sitdownTime,
                            'nowTime=', nowTime,
                            'ret=', True)
            return True

        return False

    def _getEarliestSitdownPlayer(self, table):
        ret = None
        for seat in table.seats:
            if not seat.player:
                continue
            if ret is None or seat.player.sitdownTime < ret.sitdownTime:
                ret = seat.player
        return ret

    def _onSitdownEvent(self, evt):
        evt.player.sitdownTime = int(time.time())
        chip = self.getPlayerChip(evt.table, evt.player)
        if evt.table.chipSection is None:
            evt.table.chipSection = self.getChipSection(evt.table, chip)
        if ftlog.is_debug():
            ftlog.debug('AssignTableWithChipPolicy._onSitdownEvent',
                        'seat=', (evt.player.userId, evt.player.seatId),
                        'chip=', chip,
                        'chipSection=', evt.table.chipSection)

    def _onStandupEvent(self, evt):
        if ftlog.is_debug():
            ftlog.debug('AssignTableWithChipPolicy._onStandupEvent',
                        'seat=', (evt.player.userId, evt.seat.seatId))
        evt.player.sitdownTime = 0
        if evt.table.idleSeatCount == evt.table.seatCount:
            # 桌子没人了
            evt.table.chipSection = None


class JoinTablePolicy(object):
    def canJoin(self, table, player):
        try:
            killPigLevel = table.room.roomConf.get('killPigLevel', 0)
            if killPigLevel > 0:
                return not self.isWaitPigTable(table, player, killPigLevel)
            return True
        except:
            ftlog.error('JoinTablePolicy.canJoin Exception',
                        table.tableId, killPigLevel)
            return True
        
    def isWaitPigTable(self, table, player, killPigLevel):
        levelCount = 0
        devIds = set()
        clientIps = set()
        players = table.getPlayers()
        players.append(player)
        details = []
        for p in players:
            devId = p.getData('devId', '')
            clientIp = p.getData('clientIp', '')
            score = p.getData('skillScoreInfo', {}).get('score', 0)
            if score < killPigLevel:
                levelCount += 1
            devIds.add(devId)
            clientIps.add(clientIp)
            details.append((p.userId, devId, clientIp, score))

        if levelCount >= 2:
            ftlog.warn('JoinTablePolicy.isWaitPigTable LevelPig',
                       table.tableId, killPigLevel, details)
            return True
        
        if len(devIds) != len(details):
            ftlog.warn('JoinTablePolicy.isWaitPigTable DevIdPig',
                       table.tableId, killPigLevel, details)
            return True
        
        if len(clientIps) != len(details):
            ftlog.warn('JoinTablePolicy.isWaitPigTable ClientIpPig',
                       table.tableId, killPigLevel, details)
            return True
        
        ftlog.info('JoinTablePolicy.isWaitPigTable NotWatiPig',
                   table.tableId, killPigLevel, details)

        return False

class FirstCallPolicyLuck(FirstCallPolicy):
    '''
    首叫策略，运气值
    '''
    def newPlayerFirstCall(self, table):
        # 生涯第一局首叫 [桌上‘只有’一个‘生涯第一局’，且其他两人‘生涯局数大于配置’，则首叫]
        players = [seat.player for seat in table.seats]
        players.sort(key=lambda x: x.datas.get('plays', 0))
        
        if players[0].datas.get('plays', 0) == 0:
            if players[1].datas.get('plays', 0) > table.runConf.datas.get('otherPlayersCareerRound', 3):
                return players[0].seat
    
    def chooseFirstCall(self, table):
        isNewPlayerFirstCall = self.newPlayerFirstCall(table)
        if isNewPlayerFirstCall:
            return isNewPlayerFirstCall
        
        gameRound = table.gameRound
        seats = gameRound.seats

        players = [seat.player for seat in seats]
        players.sort(key=lambda x: (x.luckValue, x.userId), reverse=True)

        if players[0].luckValue >= 10:
            players[0].luckValue = 0
            if ftlog.is_debug():
                for player in players:
                    ftlog.debug('FirstCallPolicyImpl.chooseFirstCall luckValue >= 10',
                                'roomId=', table.room.roomId,
                                'tableId=', table.tableId,
                                'userId=', player.userId,
                                'userLuckValue=', player.luckValue)
            return players[0].seat
        else:
            luckValues = [1, 2, 3]
            newLuckValues = [2, 3]
            playerRandomLuckValues = [(player, random.choice(luckValues) if player.datas.get('plays', 0) > 10 else random.choice(newLuckValues)) for player in players]
            playerRandomLuckValues.sort(key=lambda x: (x[1], x[0].userId), reverse=True)
            playerRandomLuckValues[0][0].luckValue = 0
            for player, luckValue in playerRandomLuckValues[1:]:
                player.luckValue += luckValue
            if ftlog.is_debug():
                for player, randomLuckValue in playerRandomLuckValues:
                    ftlog.debug('FirstCallPolicyImpl.chooseFirstCall',
                                'roomId=', table.room.roomId,
                                'tableId=', table.tableId,
                                'userId=', player.userId,
                                'randomLuckValue=', randomLuckValue,
                                'userLuckValue=', player.luckValue)
            return playerRandomLuckValues[0][0].seat


class FirstCallPolicyImpl(FirstCallPolicy):
    '''
    首次叫策略， 依据配置文件动态选择选择不同实现
    '''
    def __init__(self):
        self._firstCallPolicyMap = {
            'luck': FirstCallPolicyLuck(),
            'random': FirstCallPolicyRandom()
        }

    def chooseFirstCall(self, table):
        # 处理
        isAITable = table.room.roomConf.get('isAI', 0)
        if isAITable:
            for seat in table.gameRound.seats:
                if not seat.player.isAI:
                    return seat
        firstCallPolicyConf = table.runConf.datas.get('firstCallPolicyType', 'random')
        return self._firstCallPolicyMap[firstCallPolicyConf].chooseFirstCall(table)
