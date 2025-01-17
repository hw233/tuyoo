# -*- coding:utf-8 -*-
'''
Created on 2017年6月14日

@author: wangyonghui
'''
import math

import time

from dizhu.entity import dizhuconf
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.servers.util.rpc import new_table_winlose, new_table_remote
from dizhucomm.core.const import CallResult
from dizhucomm.core.events import SitdownEvent, StandupEvent
from dizhucomm.core.playmode import GameRound
from dizhucomm.core.policies import BuyinPolicy, GameResult, SettlementPolicy, CallPolicy, PunishPolicy
from dizhucomm.entity import gameexp
from dizhucomm.core.exceptions import ChipNotEnoughException, BadCallException
import freetime.util.log as ftlog
from poker.entity.dao import gamedata


class SettlementPolicyMix(SettlementPolicy):
    def __init__(self):
        super(SettlementPolicyMix, self).__init__()
        self._punishPolicy = PunishPolicyMix(False)

    def calcResult(self, gameRound):
        ret = GameResultMix(gameRound)
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

    def _calcForGameAbort(self, gameResult):
        return gameResult

    def _calcForGameOver(self, gameResult):
        # 收服务费
        roomFeeConf = dizhuconf.getRoomFeeConf()
        self._calcFee(gameResult, roomFeeConf)

        if gameResult.gameRound.table.room.roomConf.get('zeroSumFlag', 0) == 1:
            # 计算输赢
            self._calcWinloseZeroSum(gameResult)
            # 托管包赔
            self._punishPolicy.punishZeroSum(gameResult)
        else:
            # 计算输赢
            self._calcWinlose(gameResult)
            # 托管包赔
            self._punishPolicy.punish(gameResult)
        # 抽成
        self._calcWinnerTax(gameResult)
        return gameResult

    def _calcFee(self, result, roomFeeConf):
        basicRate = roomFeeConf.get('basic', 1)
        highMulti = roomFeeConf.get('high_multi', 32)

        for sst in result.seatStatements:
            sst.fee = sst.seat.player.mixConf.get('roomFee', 0)
            if sst.seat.status.totalMulti > highMulti and sst.isWin:
                sst.fixedFee += sst.seat.player.mixConf.get('fixedRoomFee', 0)
            sst.fee = min(abs(int(sst.fee * basicRate)), sst.final)
            sst.final -= sst.fee
            sst.fixedFee = min(sst.fixedFee, sst.final)
            sst.final -= sst.fixedFee
            if ftlog.is_debug():
                ftlog.debug('SettlementPolicyMix._calcFee',
                            'userId=', sst.seat.player.userId,
                            'roomId=', sst.seat.player.mixConf.get('roomId'),
                            'roomFee=', sst.seat.player.mixConf.get('roomFee', 0),
                            'fixedRoomFee=', sst.seat.player.mixConf.get('fixedRoomFee', 0),
                            'fixedFee=', sst.fixedFee,
                            'sst.final=', sst.final,
                            'sst.fee=', sst.fee,
                            'sst.feeMulti=', sst.feeMulti
                            )

    def _calcWinlose(self, gameResult):
        assert (gameResult.dizhuStatement)
        for index, sst in enumerate(gameResult.seatStatements):
            # 地主输赢本农民的积分
            seatWinlose = sst.seat.status.totalMulti * gameResult.baseScores[index]
            # 农民\地主输赢积分
            seatDelta = seatWinlose if gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN else -seatWinlose
            if sst == gameResult.dizhuStatement:
                seatDelta = seatWinlose if gameResult.gameRound.result == GameRound.RESULT_DIZHU_WIN else -seatWinlose

            if seatDelta >= 0:
                seatDelta = min(sst.final, seatDelta)
            else:
                seatDelta = min(abs(sst.final), abs(seatDelta)) * -1

            sst.deltaScore(seatDelta)
            # gameResult.systemRecovery += seatDelta
            # sst.systemPaid += seatDelta

            ftlog.info('SettlementPolicyMix._calcWinlose',
                       'roundId=', gameResult.gameRound.roundId,
                       'userId=', sst.seat.userId,
                       'dizhuUserId=', gameResult.dizhuStatement.seat.userId,
                       'result=', (type(gameResult.gameRound.result), gameResult.gameRound.result),
                       'baseScore=', gameResult.baseScores[index],
                       'totalMulti=', sst.seat.status.totalMulti,
                       'seatWinlose=', (type(seatWinlose), seatWinlose),
                       'seatDelta=', seatDelta,
                       'gameResult.systemRecovery=', seatDelta - sst.delta,
                       'systemPaid=', sst.systemPaid,
                       'delta=', sst.delta,
                       'final=', sst.final)

    def _calcWinloseZeroSum(self, gameResult):
        assert (gameResult.dizhuStatement)
        dizhuIndex = 0
        for index, sst in enumerate(gameResult.seatStatements):
            if sst == gameResult.dizhuStatement:
                dizhuIndex = index
                break

        dizhuBaseScore = gameResult.gameRound.baseScores[dizhuIndex]
        nongmingDelta = []
        for index, sst in enumerate(gameResult.seatStatements):
            if sst != gameResult.dizhuStatement:
                winCoinLimit = sst.seat.player.mixConf.get('tableConf', {}).get('winCoinLimit', 0)
                nongminBaseScore = gameResult.gameRound.baseScores[index]
                # 本农民在所有农民输赢中所占的比例
                ratio = float(sst.seat.status.totalMulti) / gameResult.dizhuStatement.seat.status.totalMulti
                # 本农民输赢积分
                if gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN:
                    seatDelta = min(sst.final, nongminBaseScore * sst.seat.status.totalMulti, int(gameResult.dizhuStatement.final * float(nongminBaseScore) * ratio / dizhuBaseScore))
                    seatDelta = min(seatDelta, int(winCoinLimit * float(nongminBaseScore) * ratio / dizhuBaseScore)) if winCoinLimit > 0 else seatDelta
                else:
                    seatDelta = min(sst.final, nongminBaseScore * sst.seat.status.totalMulti, int(gameResult.dizhuStatement.final * float(nongminBaseScore) * ratio / dizhuBaseScore))
                    seatDelta = min(seatDelta, int(winCoinLimit * float(nongminBaseScore) * ratio / dizhuBaseScore)) if winCoinLimit > 0 else seatDelta
                    seatDelta = seatDelta * -1
                sst.deltaScore(seatDelta)
                nongmingDelta.append([seatDelta, nongminBaseScore])

                ftlog.info('SettlementPolicyMix._calcWinloseZeroSum',
                           'roundId=', gameResult.gameRound.roundId,
                           'userId=', sst.seat.userId,
                           'dizhuUserId=', gameResult.dizhuStatement.seat.userId,
                           'result=', gameResult.gameRound.result,
                           'baseScore=', gameResult.baseScores[index],
                           'totalMulti=', sst.seat.status.totalMulti,
                           'seatWinlose=', seatDelta,
                           'seatDelta=', seatDelta,
                           'gameResult.systemRecovery=', seatDelta - sst.delta,
                           'systemPaid=', sst.systemPaid,
                           'delta=', sst.delta,
                           'final=', sst.final)
                assert (gameResult.dizhuStatement.final >= 0)
        dizhuTotalDeta = 0
        for delta, baseScore in nongmingDelta:
            seatDeltaDizhu = int(delta * float(dizhuBaseScore) / baseScore)
            dizhuTotalDeta += seatDeltaDizhu
        dizhuDelta = min(gameResult.dizhuStatement.final, abs(dizhuTotalDeta))
        gameResult.dizhuStatement.deltaScore(-dizhuDelta if gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN else dizhuDelta)

    def _calcWinnerTax(self, result):
        for index, sst in enumerate(result.seatStatements):
            winnerTaxRate = result.gameRound.winnerTaxMultis[index]
            if winnerTaxRate:
                if sst.delta > 0:
                    sst.winnerTax = min(sst.delta, int(sst.delta * winnerTaxRate))
                    if sst.winnerTax > 0:
                        sst.final -= sst.winnerTax

    def _settlementForGameAbort(self, gameResult):
        for sst in gameResult.seatStatements:
            sst.seat.player.score = sst.final
            new_table_remote._setLastTableChip(sst.seat.player.userId, True, sst.final)

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
        for index, sst in enumerate(gameResult.seatStatements):
            seatStatus = sst.seat.status
            outCardTimes.append(seatStatus.outCardTimes)
        maxOutCardTimes = max(outCardTimes)

        for index, sst in enumerate(gameResult.seatStatements):
            # 服务费
            userId = sst.seat.userId
            clientId = sst.seat.player.clientId
            sst.seat.player.score = sst.final
            mixConfRoomId = sst.seat.player.mixConf.get('roomId')

            assist = 0
            validMaxOutCard = 0
            seatStatus = sst.seat.status
            if sst != gameResult.dizhuStatement and len(seatStatus.cards) != 0 and sst.isWin:
                assist = 1
            if seatStatus.outCardTimes == maxOutCardTimes and sst.isWin:
                validMaxOutCard = 1

            finalTableChip, finalChip, expInfo, skillScoreInfo \
                = new_table_winlose.doTableWinloseUT(userId, roomId, tableId, roundNum, clientId,
                                                     sst.isWin, sst.winStreak, winUserId, sst == gameResult.dizhuStatement,
                                                     sst.fee, sst.cardNoteFee, sst.delta, sst.systemPaid, sst.winnerTax,
                                                     gameResult.gameRound.baseScores[index], sst.seat.status.totalMulti,
                                                     bombCount, chuntian, gameResult.slams[index], playMode, topCardList,
                                                     mixConfRoomId=mixConfRoomId, fixedFee=sst.fixedFee, assist=assist,
                                                     outCardSeconds=seatStatus.outCardSeconds, validMaxOutCard=validMaxOutCard)
            ftlog.info('SettlementPolicyMix._settlementForGameOver',
                       'roomId=', gameResult.gameRound.table.roomId,
                       'tableId=', gameResult.gameRound.table.tableId,
                       'roundId=', gameResult.gameRound.roundId,
                       'cardNoteFee=', sst.cardNoteFee,
                       'mixConfRoomId=', mixConfRoomId,
                       'fee=', sst.fee,
                       'fixedFee=', sst.fixedFee,
                       'delta=', sst.delta,
                       'winnerTax=', sst.winnerTax,
                       'baseScore=', gameResult.gameRound.baseScores[index],
                       'totalMulti=', sst.seat.status.totalMulti,
                       'sstFinal=', sst.final,
                       'userId=', userId,
                       'winStreak=', gamedata.getGameAttrInt(sst.seat.player.userId, DIZHU_GAMEID, 'winstreak'),
                       'finalTableChip=', finalTableChip,
                       'finalChip=', finalChip)
            sst.skillscoreInfo = skillScoreInfo
            sst.seat.player.chip = finalChip
            sst.seat.player.score = sst.final = finalTableChip
            explevel, title = gameexp.getLevelInfo(DIZHU_GAMEID, expInfo[0])
            nextExp = gameexp.getNextLevelExp(DIZHU_GAMEID, explevel)
            sst.expInfo = [explevel, expInfo[0], expInfo[1], nextExp, title]
            pt = sst.seat.player.datas.get('plays', 0)
            sst.seat.player.datas['plays'] = pt + 1
            sst.winStreak = gamedata.getGameAttrInt(sst.seat.player.userId, DIZHU_GAMEID, 'winstreak')
            if sst.isWin:
                wt = sst.seat.player.datas.get('wins', 0)
                sst.seat.player.datas['wins'] = wt + 1


class BuyinPolicyMix(BuyinPolicy):
    def buyin(self, table, player, seat, continueBuyin):
        roomBuyInChip = player.mixConf.get('buyinchip', 0)
        roomMinCoin = player.mixConf.get('minCoin', 0)
        kickOutCoin = player.mixConf.get('kickOutCoin', 0)
        playerChip = player.chip

        minCoin = roomMinCoin
        # 兼容老客户端
        last_table_chip = player.score if player.score else new_table_remote._getLastTableChip(player.userId, True)
        # 根据 continueBuyin 判断 buyinChip
        buyinChip = roomBuyInChip
        if continueBuyin:
            minCoin = kickOutCoin
            buyInToRoomBuyIn = player.mixConf.get('continueFillUp', 0)
            if buyInToRoomBuyIn:
                # 房间点击继续按钮补满金币开关,和传入的continueBuyin不同意义
                buyinChip = max(roomBuyInChip, last_table_chip)
            elif last_table_chip >= kickOutCoin:
                buyinChip = last_table_chip
            elif last_table_chip < kickOutCoin and playerChip >= minCoin:
                buyinChip = roomBuyInChip
            else:
                # last_table_chip 小于踢出值并且playerChip小于带入值，raise 错误
                ftlog.warn('BuyinPolicyMix ',
                           'userId=', player.userId,
                           'roomId=', table.roomId,
                           'clientId=', player.clientId,
                           'last_table_chip=', last_table_chip,
                           'playerScore=', player.score,
                           'playerChip=', playerChip,
                           'kickOutCoin=', kickOutCoin,
                           'roomMinCoin=', roomMinCoin,
                           'roomBuyInChip=', roomBuyInChip,
                           'continueBuyin=', continueBuyin)
                raise ChipNotEnoughException('金币不足， 踢出房间')

        if ftlog.is_debug():
            ftlog.debug('BuyinPolicyMix ',
                        'userId=', player.userId,
                        'roomId=', table.roomId,
                        'clientId=', player.clientId,
                        'last_table_chip=', last_table_chip,
                        'playerScore=', player.score,
                        'buyinChip=', buyinChip,
                        'continueBuyin=', continueBuyin)

        tchip, chip, _ = new_table_remote.buyin(player.userId,
                                                player.mixConf.get('roomId') or table.roomId,
                                                player.clientId,
                                                table.tableId,
                                                buyinChip,
                                                minCoin,
                                                continueBuyin)
        player.score = tchip
        player.chip = chip
        player.datas['chip'] = chip
        player.datas['buyinMark'] = 1
        player.datas['buyinChip'] = tchip

        if continueBuyin and (buyinChip == roomBuyInChip or last_table_chip == roomBuyInChip):
            player.datas['buyinTip'] = ''
        else:
            player.datas['buyinTip'] = self._buildBuyinTip(roomBuyInChip, tchip, chip, continueBuyin)

    def cashin(self, table, player, seat):
        final = new_table_remote.cashin(player.userId, player.mixConf.get('roomId') or table.roomId, player.clientId, table.tableId, player.score)
        player.chip = final
        if ftlog.is_debug():
            ftlog.debug('BuyinPolicyMix.cashin',
                        'userId=', player.userId,
                        'roomId=', table.roomId,
                        'tableId=', table.tableId,
                        'playerScore=', player.score,
                        'playerChip=', player.chip)

    def _buildBuyinTip(self, roomBuyInChip, buyinChip, chip, continueBuyin):
        buyinConf = dizhuconf.getBuyInConf()
        if buyinChip == roomBuyInChip:
            if continueBuyin:
                return buyinConf.get('tip_auto', '')
            else:
                return buyinConf.get('tip', '').format(BUYIN_CHIP=buyinChip)
        else:
            if chip <= 0:
                if continueBuyin:
                    return buyinConf.get('tip_auto_all_next', '')
                else:
                    return buyinConf.get('tip_auto_all', '')
        return ''

class GameResultMix(GameResult):
    def __init__(self, gameRound):
        super(GameResultMix, self).__init__(gameRound)
        self.gameRound = gameRound
        self.slamMultis = gameRound.slamMultis
        self.slams = [gameRound.totalMulti >= slamMulti for slamMulti in self.slamMultis]
        self.baseScores = gameRound.baseScores


class CallPolicyErdouMix(CallPolicy):
    def call(self, table, callValue, oper):
        '''
        玩家叫地主
        @return: (CallResult, NextCallSeat)
        '''
        gameRound = table.gameRound
        seats = gameRound.seats
        try:
            rangpaiMultiType = seats[0].player.mixConf.get('tableConf', {}).get('rangpaiMultiType', 1)
        except:
            rangpaiMultiType = 2

        assert (len(seats) == 2)
        assert (gameRound.curOpSeat)
        # 有状态机控制，必须<5
        assert (len(gameRound.callList) < 5)
        # 必须是0, 或则1
        # 老版本是当前的倍数或者当前+1
        if callValue < 0 or callValue > math.pow(2, len(gameRound.callList)) * table.runConf.firstCallValue:
            raise BadCallException()

        callValue = min(callValue, 1)
        gameRound.addCall(gameRound.curOpSeat, callValue)
        if callValue > 0:
            if len(gameRound.effectiveCallList) == 1:
                gameRound.callMulti = table.runConf.firstCallValue
            else:
                if rangpaiMultiType == 1:
                    gameRound.callMulti += 1
                else:
                    gameRound.callMulti *= 2

        # 还有人没叫
        if len(gameRound.callList) < 2:
            return CallResult.CALLING, gameRound.curOpSeat.next

        # 所有人都叫过地主了, 如果没人叫则流局
        if not gameRound.lastEffectiveCall:
            return CallResult.ABORT, None

        if callValue > 0:
            gameRound.rangpai = gameRound.rangpai + 1

        # 有人不叫或者叫过5次以上就结束
        if callValue == 0 or len(gameRound.callList) >= 5:
            gameRound.dizhuSeat = gameRound.lastEffectiveCall[0]
            return CallResult.FINISH, None

        # 有人已经放弃了叫地主
        if gameRound.callList[-2][1] == 0:
            gameRound.dizhuSeat = gameRound.lastEffectiveCall[0]
            return CallResult.FINISH, None

        return CallResult.CALLING, gameRound.curOpSeat.next


class PunishPolicyMix(PunishPolicy):
    def __init__(self, canNagtive):
        self._canNagtive = canNagtive

    def punish(self, gameResult):
        '''
        根据gameResult进行惩罚
        '''
        punishNM = []
        notPunishNM = []
        for index, sst in enumerate(gameResult.seatStatements):
            if sst != gameResult.dizhuStatement:
                if sst.seat.status.isPunish:
                    punishNM.append([index, sst])
                else:
                    notPunishNM.append([index, sst])
        # 地主胜利，一个农民托管

        if (len(punishNM) == 1
            and len(notPunishNM) == 1
            and gameResult.gameRound.result == GameRound.RESULT_DIZHU_WIN):
            punishNM[0][1].isPunish = True
            if self._canNagtive:
                # 直接转嫁
                if notPunishNM[0][1].delta < 0:
                    punishNM[0][1].deltaScore(notPunishNM[0][1].delta)
                    notPunishNM[0][1].deltaScore(-notPunishNM[0][1].delta)
            else:
                # 计算可以转嫁多少
                beishu = abs(notPunishNM[0][1].delta / gameResult.gameRound.baseScores[notPunishNM[0][0]])
                punishBaseScore = gameResult.gameRound.baseScores[punishNM[0][0]]
                punishNM[0][1].deltaScore(min(abs(punishBaseScore * beishu), punishNM[0][1].final) * -1)
                notPunishNM[0][1].deltaScore(-notPunishNM[0][1].delta)
        elif (len(punishNM) == 1
            and len(notPunishNM) == 1
            and gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN):

            if gameResult.gameRound.table.room.roomConf.get('nongminWinAlone'):
                # 农民胜利 一个农民托管包赔 另一个农民赢地主输的全部金币
                punishNM[0][1].isPunish = True

                # winCoinLimit = notPunishNM[0][1].seat.player.mixConf.get('tableConf', {}).get('winCoinLimit', 0)
                # notPunishDelta = min(winCoinLimit, winCoinLimit - notPunishNM[0][1].delta) if winCoinLimit else notPunishNM[0][1].delta
                notPunishDelta = notPunishNM[0][1].delta
                notPunishNM[0][1].deltaScore(notPunishDelta)
                gameResult.systemRecovery += notPunishDelta

                punishNM[0][1].deltaScore(-punishNM[0][1].delta)
                gameResult.systemRecovery -= punishNM[0][1].delta

            else:
                # 农民胜利 一个农民托管包赔 另一个农民正常赢
                punishNM[0][1].deltaScore(-punishNM[0][1].delta)
                gameResult.systemRecovery -= punishNM[0][1].delta

        elif (len(punishNM) == 2
            and len(notPunishNM) == 0
            and gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN):
            # gameResult.systemRecovery += punishNM[0][1].delta
            punishNM[0][1].deltaScore(-punishNM[0][1].delta)

            # gameResult.systemRecovery += punishNM[1][1].delta
            punishNM[1][1].deltaScore(-punishNM[1][1].delta)

    def punishZeroSum(self, gameResult):
        '''
        根据gameResult进行惩罚
        '''
        punishNM = []
        notPunishNM = []
        dizhu = []
        for index, sst in enumerate(gameResult.seatStatements):
            if sst != gameResult.dizhuStatement:
                if sst.seat.status.isPunish:
                    punishNM.append([index, sst])
                else:
                    notPunishNM.append([index, sst])
            else:
                dizhu.append([index, sst])
        # 地主胜利，一个农民托管
        if (len(punishNM) == 1
            and len(notPunishNM) == 1
            and gameResult.gameRound.result == GameRound.RESULT_DIZHU_WIN):
            punishNM[0][1].isPunish = True
            if self._canNagtive:
                # 直接转嫁
                if notPunishNM[0][1].delta < 0:
                    punishNM[0][1].deltaScore(notPunishNM[0][1].delta)
                    notPunishNM[0][1].deltaScore(-notPunishNM[0][1].delta)
            else:
                # 计算可以转嫁多少, 计算
                punishBaseScore = gameResult.gameRound.baseScores[punishNM[0][0]]
                notPunishNMBaseScore = gameResult.gameRound.baseScores[notPunishNM[0][0]]
                dizhuBaseScore = gameResult.gameRound.baseScores[dizhu[0][0]]
                score = min(abs(int(float(punishBaseScore) / notPunishNMBaseScore * notPunishNM[0][1].delta)), punishNM[0][1].final) * -1
                punishNM[0][1].deltaScore(score)
                gameResult.dizhuStatement.deltaScore(int(-score * float(dizhuBaseScore) / punishBaseScore))

                seatDeltaDizhu = int(notPunishNM[0][1].delta * float(dizhuBaseScore) / notPunishNMBaseScore)
                gameResult.dizhuStatement.deltaScore(seatDeltaDizhu)
                notPunishNM[0][1].deltaScore(-notPunishNM[0][1].delta)
        elif (len(punishNM) == 1
            and len(notPunishNM) == 1
            and gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN):

            if gameResult.gameRound.table.room.roomConf.get('nongminWinAlone'):
                # 农民胜利 一个农民托管包赔 另一个农民赢地主输的全部金币
                punishNM[0][1].isPunish = True

                # winCoinLimit = notPunishNM[0][1].seat.player.mixConf.get('tableConf', {}).get('winCoinLimit', 0)
                # notPunishDelta = min(winCoinLimit, winCoinLimit - notPunishNM[0][1].delta) if winCoinLimit else notPunishNM[0][1].delta
                notPunishDelta = notPunishNM[0][1].delta
                notPunishNM[0][1].deltaScore(notPunishDelta)
                gameResult.systemRecovery += notPunishDelta

                punishNM[0][1].deltaScore(-punishNM[0][1].delta)
                gameResult.systemRecovery -= punishNM[0][1].delta

            else:
                # 农民胜利 一个农民托管包赔 另一个农民正常赢
                punishNM[0][1].deltaScore(-punishNM[0][1].delta)
                gameResult.systemRecovery -= punishNM[0][1].delta

        elif (len(punishNM) == 2
            and len(notPunishNM) == 0
            and gameResult.gameRound.result == GameRound.RESULT_NONGMIN_WIN):
            punishNM[0][1].deltaScore(-punishNM[0][1].delta)
            punishNM[1][1].deltaScore(-punishNM[1][1].delta)


class AssignTableWithMixIdPolicy(object):
    '''
    混房按mixId配桌
    '''
    def setupTable(self, table):
        table.mixIdSection = None
        table.on(SitdownEvent, self._onSitdownEvent)
        table.on(StandupEvent, self._onStandupEvent)

    def getMixIdSection(self, table, player):
        '''
        获取mixId区间，用来赋值给桌子 mixIdSection 属性
        '''
        mixIdAssignTableConf = None
        try:
            mixIdAssignTableConf = self.getMixIdAssignTableConf(table)
            if mixIdAssignTableConf:
                for section in mixIdAssignTableConf.get('sections', []):
                    if section[0] == player.mixConf.get('mixId'):
                        if ftlog.is_debug():
                            ftlog.debug('AssignTableWithMixIdPolicy.getMixIdSection',
                                        'tableId=', table.tableId,
                                        'section=', section,
                                        'mixIdAssignTableConf=', mixIdAssignTableConf)
                        return section
            return None
        except:
            ftlog.error('AssignTableWithMixIdPolicy.getMixIdSection',
                        'tableId=', table.tableId,
                        'mixIdAssignTableConf=', mixIdAssignTableConf)
            return None

    def getMixIdAssignTableConf(self, table):
        return table.runConf.datas.get('mixIdAssignTable')

    def getTimeoutThreshold(self, table):
        mixIdAssignTableConf = self.getMixIdAssignTableConf(table)
        if not mixIdAssignTableConf:
            return 0
        return mixIdAssignTableConf.get('timeout', -1)

    def getTimeoutForIdThreshold(self, table):
        mixIdAssignTableConf = self.getMixIdAssignTableConf(table)
        if not mixIdAssignTableConf:
            return 0
        return mixIdAssignTableConf.get('timeoutForId', -1)

    def canJoin(self, table, player):
        nowTime = int(time.time())

        # 空桌子可以坐下
        if table.idleSeatCount == table.seatCount:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithMixIdPolicy.canJoin EmptyTable',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True

        # mixId区间
        if not table.mixIdSection:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithMixIdPolicy.canJoin EmptyTableMixIdSection',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'ret=', True)
            return True

        earliesPlayer = self._getEarliestSitdownPlayer(table)
        assert earliesPlayer

        # 桌子等待时间超过阈值 -1 表示无限大
        timeoutForIdThreshold = self.getTimeoutForIdThreshold(table)
        if timeoutForIdThreshold > 0 and nowTime - earliesPlayer.sitdownTime <= timeoutForIdThreshold:
            earliesPlayerIds = self._getEarliestSitdownPlayerIds(table)  # 获取坐下的用户Id
            for mixId in table.mixIdSection:
                if mixId == player.mixConf.get('mixId') == 'xingyao':
                    # 在一段时间内
                    for uid in earliesPlayerIds:
                        if len(str(uid)) > 3 and len(str(player.userId)) > 3 and len(str(player.userId)) == len(str(uid)) and str(uid)[:3] == str(player.userId)[:3]:
                            if ftlog.is_debug():
                                ftlog.debug('AssignTableWithMixIdPolicy.canJoin userId are closed',
                                            'tableId=', table.tableId,
                                            'userId=', player.userId,
                                            'mixId=', player.mixConf.get('mixId'),
                                            'mixIdSection=', table.mixIdSection,
                                            'earliesPlayerIds=', earliesPlayerIds,
                                            'timeUsed=', nowTime - earliesPlayer.sitdownTime,
                                            'ret=', False)
                            return False

        # 玩家mixId在该桌子的相应配置内
        for mixId in table.mixIdSection:
            if mixId == player.mixConf.get('mixId'):
                if ftlog.is_debug():
                    ftlog.debug('AssignTableWithMixIdPolicy.canJoin InTableMixIdSection',
                                'tableId=', table.tableId,
                                'userId=', player.userId,
                                'mixId=', mixId,
                                'mixIdSection=', table.mixIdSection,
                                'ret=', True)
                return True

        # 桌子等待时间超过阈值 -1 表示无限大
        timeoutThreshold = self.getTimeoutThreshold(table)
        if timeoutThreshold < 0:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithMixIdPolicy.canJoin InfinityTimeout',
                            'tableId=', table.tableId,
                            'userId=', player.userId,
                            'timeoutThreshold=', timeoutThreshold,
                            'ret=', False)
            return False

        if nowTime - earliesPlayer.sitdownTime >= timeoutThreshold:
            if ftlog.is_debug():
                ftlog.debug('AssignTableWithMixIdPolicy.canJoin OverTimeout',
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

    def _getEarliestSitdownPlayerIds(self, table):
        ret = []
        for seat in table.seats:
            if not seat.player:
                continue
            ret.append(seat.player.userId)
        return ret

    def _onSitdownEvent(self, evt):
        evt.player.sitdownTime = int(time.time())
        if evt.table.mixIdSection is None:
            evt.table.mixIdSection = self.getMixIdSection(evt.table, evt.player)
        if ftlog.is_debug():
            ftlog.debug('AssignTableWithMixIdPolicy._onSitdownEvent',
                        'seat=', (evt.player.userId, evt.player.seatId),
                        'mixId=', evt.player.mixConf.get('mixId'),
                        'mixIdSection=', evt.table.mixIdSection)

    def _onStandupEvent(self, evt):
        if ftlog.is_debug():
            ftlog.debug('AssignTableWithMixIdPolicy._onStandupEvent',
                        'seat=', (evt.player.userId, evt.seat.seatId))
        evt.player.sitdownTime = 0
        if evt.table.idleSeatCount == evt.table.seatCount:
            # 桌子没人了
            evt.table.mixIdSection = None
