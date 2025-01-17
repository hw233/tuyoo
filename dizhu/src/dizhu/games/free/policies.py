# -*- coding:utf-8 -*-
'''
Created on 2017年3月7日

@author: zhaojiangang
'''
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.servers.util.rpc import new_table_winlose
from dizhucomm.core.playmode import GameRound
from dizhucomm.core.policies import GameResult, BuyinPolicy, SettlementPolicy
from dizhucomm.entity import gameexp
from dizhucomm.playmodes.base import PunishPolicyNormal
import freetime.util.log as ftlog


class SettlementPolicyFree(SettlementPolicy):
    def __init__(self):
        super(SettlementPolicyFree, self).__init__()
        self._punishPolicy = PunishPolicyNormal(True)
    
    def calcResult(self, gameRound):
        ret = GameResult(gameRound)
        if gameRound.firstWinSeat:
            self._calcForGameOver(ret)
        else:
            self._calcForGameAbort(ret)
        return ret
    
    def settlement(self, gameResult):
        if gameResult.gameRound.firstWinSeat:
            self._settlementForGameOver(gameResult)
        else:
            self._settlementForGameAbort(gameResult)

    def _settlementForGameAbort(self, gameResult):
        for sst in gameResult.seatStatements:
            sst.seat.player.score = sst.final

    def _settlementForGameOver(self, gameResult):
        roomId = gameResult.gameRound.table.roomId
        tableId = gameResult.gameRound.table.tableId
        roundNum = gameResult.gameRound.roundNum
        winUserId = gameResult.gameRound.firstWinSeat.userId
        bombCount = gameResult.gameRound.bombCount
        chuntian = 2 if gameResult.gameRound.isChuntian else 1
        playMode = gameResult.gameRound.table.playMode.name
        topCardList = gameResult.gameRound.topValidCards.cards

        outCardTimes = []
        for sst in gameResult.seatStatements:
            seatStatus = sst.seat.status
            outCardTimes.append(seatStatus.outCardTimes)
        maxOutCardTimes = max(outCardTimes)
        
        for sst in gameResult.seatStatements:
            userId = sst.seat.userId
            clientId = sst.seat.player.clientId

            assist = 0
            validMaxOutCard = 0
            seatStatus = sst.seat.status
            if sst != gameResult.dizhuStatement and len(seatStatus.cards) != 0 and sst.isWin:
                assist = 1
            if seatStatus.outCardTimes == maxOutCardTimes and sst.isWin:
                validMaxOutCard = 1

            finalChip, expInfo, skillScoreInfo \
                = new_table_winlose.doFreeTableWinloseUT(userId, roomId, tableId, roundNum, clientId,
                                                         winUserId, sst.isWin, sst.winStreak, sst == gameResult.dizhuStatement,
                                                         sst.delta, sst.final, gameResult.gameRound.baseScore,
                                                         sst.seat.status.totalMulti, bombCount, chuntian, gameResult.slam,
                                                         playMode, topCardList, assist=assist, validMaxOutCard=validMaxOutCard)
            ftlog.info('SettlementPolicyFree._settlementForGameOver',
                       'roomId=', gameResult.gameRound.table.roomId,
                       'tableId=', gameResult.gameRound.table.tableId,
                       'roundId=', gameResult.gameRound.roundId,
                       'winStreak=', sst.winStreak,
                       'fee=', sst.fee,
                       'delta=', sst.delta,
                       'winnerTax=', sst.winnerTax,
                       'baseScore=', gameResult.gameRound.baseScore,
                       'totalMulti=', sst.seat.status.totalMulti,
                       'sstFinal=', sst.final,
                       'userId=', userId,
                       'finalChip=', finalChip)
            sst.skillscoreInfo = skillScoreInfo
            sst.seat.player.chip = finalChip
            sst.seat.player.score = sst.final
            explevel, title = gameexp.getLevelInfo(DIZHU_GAMEID, expInfo[0])
            nextExp = gameexp.getNextLevelExp(DIZHU_GAMEID, explevel)
            sst.expInfo = [explevel, expInfo[0], expInfo[1], nextExp, title]
            pt = sst.seat.player.datas.get('plays', 0)
            sst.seat.player.datas['plays'] = pt + 1
            if sst.isWin:
                wt = sst.seat.player.datas.get('wins', 0)
                sst.seat.player.datas['wins'] = wt + 1
            sst.seat.player.score = sst.final
        ftlog.info('SettlementPolicyFree._settlementForGameOver',
                   'roomId=', gameResult.gameRound.table.roomId,
                   'tableId=', gameResult.gameRound.table.tableId,
                   'roundId=', gameResult.gameRound.roundId,
                   'infos=', [(sst.seat.userId, sst.seat.player.score, sst.delta) for sst in gameResult.seatStatements])

    def _calcWinlose(self, gameResult):
        assert(gameResult.dizhuStatement)
        for sst in gameResult.seatStatements:
            if sst != gameResult.dizhuStatement:
                # 地主输赢本农民的积分
                seatWinlose = sst.seat.status.totalMulti * gameResult.baseScore
                if ftlog.is_debug():
                    ftlog.debug('SettlementPolicyFree._calcWinlose',
                                'roundId=', gameResult.gameRound.roundId,
                                'userId=', sst.seat.userId,
                                'dizhuUserId=', gameResult.dizhuStatement.seat.userId,
                                'result=', (type(gameResult.gameRound.result), gameResult.gameRound.result),
                                'baseScore=', gameResult.baseScore,
                                'totalMulti=', sst.seat.status.totalMulti,
                                'seatWinlose=', (type(seatWinlose), seatWinlose))
                # 本农民输赢积分
                seatDelta = seatWinlose if gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN else -seatWinlose
                sst.delta = seatDelta
                sst.final += seatDelta
                gameResult.dizhuStatement.delta -= seatDelta
                gameResult.dizhuStatement.final -= seatDelta

    def _calcForGameAbort(self, gameResult):
        return gameResult
    
    def _calcForGameOver(self, gameResult):
        # 收服务费
        # 计算输赢
        self._calcWinlose(gameResult)
        # 托管包赔
        self._punishPolicy.punish(gameResult)
        return gameResult

class BuyinPolicyFree(BuyinPolicy):
    def buyin(self, table, player, seat, continueBuyin):
        if not continueBuyin:
            player.score = table.room.roomConf['initScore']
        if player.score <= 0:
            player.score = table.room.roomConf['initScore']
            player.datas['buyinMark'] = 1
            player.datas['buyinChip'] = player.score
            player.datas['buyinTip'] = '系统重新给您补充了积分'

        if ftlog.is_debug():
            ftlog.debug('BuyinPolicyFree.buyin',
                        'roomId=', table.roomId,
                        'tableId=', table.tableId,
                        'seat=', (seat.userId, seat.seatId),
                        'continueBuyin=', continueBuyin,
                        'score=', player.score)
    def cashin(self, table, player, seat):
        pass


