# -*- coding:utf-8 -*-
'''
Created on 2017年6月13日

@author: wangyonghui
'''
import copy

from dizhu.entity import dizhu_score_ranking, dizhuconf, dizhu_giftbag
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhucomm import playmodes
from dizhucomm.core import bug_fix
from hall.entity import hallconf
from dizhu.servers.util.rpc import task_remote, new_table_remote
from dizhu.servers.util.rpc import new_table_winlose
from dizhu.games.normalbase.tableproto import DizhuTableProtoNormalBase
from poker.entity.configure import configure
from poker.entity.dao import gamedata
from poker.protocol import router
from dizhucomm.entity import tablepay, emoji
import freetime.util.log as ftlog
import dizhu.entity.skillscore as skillscore
from dizhucomm.entity import treasurebox
from poker.util import strutil


class DizhuTableProtoMix(DizhuTableProtoNormalBase):
    def __init__(self, tableCtrl):
        super(DizhuTableProtoMix, self).__init__(tableCtrl)

    def buildResultDetails(self, result):
        luckyItemArgs = []
        winStreak = []
        skillScoreInfos = []
        cards = []
        addCoupons = []
        seatDetails = []
        seatInfos = []
        for index, sst in enumerate(result.seatStatements):
            waittime = sst.seat.player.mixConf.get('tableConf', {}).get('optimeCall', 15)
            if sst.final < sst.seat.player.mixConf.get('tableConf', {}).get('minCoin', 0):
                waittime = int(waittime / 3)

            datas = {}
            try:
                datas = new_table_winlose.queryDataAfterWinlose(sst.seat.userId,
                                                                sst.seat.player.mixConf.get('roomId'),
                                                                sst.isWin,
                                                                sst.winStreak,
                                                                result.slams[index],
                                                                result.isChuntian,
                                                                sst.seat.player.clientId)
            except Exception, e:
                ftlog.warn('DizhuTableProtoMix.buildResultDetails',
                           'userId=', sst.seat.player.userId,
                           'roomId=', self.roomId,
                           'tableId=', self.tableId,
                           'ex=', str(e))


            tbbox = datas.get('tbbox', [0, 0])
            details = [
                sst.delta,
                sst.final,
                0,  # addcoupons[i],
                waittime,
                tbbox[0],
                tbbox[1],
                sst.expInfo[0], sst.expInfo[1], sst.expInfo[2], sst.expInfo[3], sst.expInfo[4],
                sst.seat.player.chip
            ]

            # 地主v3.773特效需要知道上一个大师分等级图标
            # 传两个大图
            skilscoreinfo = sst.skillscoreInfo
            masterlevel = skilscoreinfo['level']
            curlevelpic = skillscore.get_skill_score_big_level_pic(masterlevel)
            lastlevelpic = skillscore.get_skill_score_big_level_pic(masterlevel - 1)
            skilscoreinfo['lastbiglevelpic'] = lastlevelpic
            skilscoreinfo['curbiglevelpic'] = curlevelpic

            seatDetails.append(details)
            winStreak.append(sst.winStreak)
            skillScoreInfos.append(skilscoreinfo)
            cards.append(sst.seat.status.cards)
            addCoupons.append(0)
            seatInfos.append({'punished': 1} if sst.isPunish else {})
            luckyItemArgs.append(datas.get('luckyArgs', {}))

        return {
            'winStreak': winStreak,
            'luckyItemArgs': luckyItemArgs,
            'skillScoreInfos': skillScoreInfos,
            'addcoupons': addCoupons,
            'cards': cards,
            'seatDetails': seatDetails,
            'seatInfos': seatInfos
        }

    def sendWinloseRes(self, result):
        details = self.buildResultDetails(result)
        mp = self.buildWinloseRes(result, details, 1)
        # 免费场开关
        freeFeeSwitch = self.table.room.roomConf.get('freeFeeSwitch', 0)
        mp.setResult('free', freeFeeSwitch)
        from dizhu.game import TGDizhu
        from dizhu.entity.common.events import ActiveEvent
        crossPlayCount = configure.getGameJson(DIZHU_GAMEID, 'wx.cross', {}).get('crossPlayCount', 10)
        crossDelaySeconds = configure.getGameJson(DIZHU_GAMEID, 'wx.cross', {}).get('crossDelaySeconds', 10)
        authPlayCount = configure.getGameJson(DIZHU_GAMEID, 'authorization', {}).get('authPlayCount', 5)
        rewards = configure.getGameJson(DIZHU_GAMEID, 'authorization', {}).get('rewards', {})
        for index, seat in enumerate(self.table.seats):
            isKickOutCoin = 0

            # 每次进来需要重新初始化
            realSeats = []
            seatIndexes = []
            for i, seatDetails in enumerate(details.get('seatDetails', [])):
                copyDetail = copy.copy(seatDetails)
                realSeats.append(copyDetail)
                seatIndexes.append(i)
                mp.setResult('seat%s' % (i + 1), copyDetail)
            seatIndexes.remove(index)

            if self.table.room.roomConf.get('zeroSumFlag', 0) == 1:
                currentBaseScore = result.gameRound.baseScores[index]
                for seatIndex in seatIndexes:
                    otherBaseScore = result.gameRound.baseScores[seatIndex]
                    realSeats[seatIndex][0] = int(float(currentBaseScore) / otherBaseScore * realSeats[seatIndex][0])
                    realSeats[seatIndex][1] = int(float(currentBaseScore) / otherBaseScore * realSeats[seatIndex][1])
            else:
                # 显示以当前seat为基准做假数据
                dizhuIndex = mp.getResult('stat').get('dizhu')
                currentSeat = realSeats[index]
                windoubles = mp.getResult('windoubles')
                currentBaseScore = self.table.gameRound.baseScores[index]
                currentIsDizhu = dizhuIndex == index + 1
                dizhuwin = mp.getResult('dizhuwin')
                realDeltas = [realSeat[0] for realSeat in realSeats]
                if ftlog.is_debug():
                    ftlog.debug('DizhuTableProtoMix.sendWinloseRes realDeltas=', realDeltas,
                                'userId=', seat.player.userId,
                                'mixId=', seat.player.mixConf.get('mixId'), 'index=', index)

                if len(realDeltas) == 2:
                    for index2, realSeat in enumerate(realSeats):
                        if index != index2:
                            realSeat[0] = abs(currentSeat[0]) * (realSeat[0] / abs(realSeat[0]))
                else:
                    if realDeltas.count(0) == 0:
                        for index2, realSeat in enumerate(realSeats):
                            if index != index2:
                                if currentIsDizhu:
                                    realSeat[0] = abs(currentSeat[0] / 2) * (realSeat[0] / abs(realSeat[0]))
                                else:
                                    if dizhuIndex == index2 + 1:
                                        realSeat[0] = abs(currentSeat[0] * 2) * (realSeat[0] / abs(realSeat[0]))
                                    else:
                                        realSeat[0] = abs(currentSeat[0]) * (realSeat[0] / abs(realSeat[0]))

                    elif realDeltas.count(0) == 1:  # 一个人托管
                        for index2, realSeat in enumerate(realSeats):
                            if index != index2:
                                if currentIsDizhu:  # 地主肯定有值
                                    if realSeat[0] != 0:
                                        if dizhuwin:
                                            realSeat[0] = abs(currentSeat[0]) * (realSeat[0] / abs(realSeat[0]))
                                        else:
                                            realSeat[0] = abs(currentSeat[0] / 2) * (realSeat[0] / abs(realSeat[0]))
                                else:
                                    if currentSeat[0] == 0:
                                        if dizhuIndex == index2 + 1:
                                            realSeat[0] = abs(windoubles * 2 * currentBaseScore) * (realSeat[0] / abs(realSeat[0]))
                                        else:
                                            if dizhuwin:
                                                realSeat[0] = abs(windoubles * 2 * currentBaseScore) * (realSeat[0] / abs(realSeat[0]))
                                            else:
                                                realSeat[0] = abs(windoubles * currentBaseScore) * (realSeat[0] / abs(realSeat[0]))
                                    else:
                                        if dizhuIndex == index2 + 1:
                                            if dizhuwin:
                                                realSeat[0] = abs(currentSeat[0]) * 1 * (realSeat[0] / abs(realSeat[0]))
                                            else:
                                                realSeat[0] = abs(currentSeat[0]) * 2 * (realSeat[0] / abs(realSeat[0]))
                    else:
                        for index2, realSeat in enumerate(realSeats):
                            if realSeat[0]:
                                realSeat[0] = abs(windoubles * 2 * currentBaseScore) * (realSeat[0] / abs(realSeat[0]))

                if ftlog.is_debug():
                    fakeDeltas = []
                    for i, seatDetails in enumerate(details.get('seatDetails', [])):
                        fakeDeltas.append(mp.getResult('seat%s' % (i + 1))[0])
                    ftlog.debug('DizhuTableProtoMix.sendWinloseRes fakeDeltas=', fakeDeltas, 'userId=', seat.player.userId, 'mixId=', seat.player.mixConf.get('mixId'), 'index=', index)

            if seat.player and not seat.isGiveup:
                ssts = result.seatStatements

                # 是否达到踢出值
                isLowerKickOutCoin = True if ssts[index].final < seat.player.mixConf.get('kickOutCoin', 0) else False

                # 不踢出
                if isLowerKickOutCoin and seat.player.chip < seat.player.mixConf.get('buyinchip', 0):
                    isKickOutCoin = 1

                mp.setResult('kickOutCoinTip', '')
                if isLowerKickOutCoin and seat.player.chip >= seat.player.mixConf.get('buyinchip', 0):
                    mp.setResult('kickOutCoinTip', '点击继续，将自动将您\n桌面金币补充至%s。\n继续努力吧！' % seat.player.mixConf.get('buyinchip'))

                # 是否达到踢出值
                mp.setResult('isKickOutCoin', isKickOutCoin)
                # 破产埋点Id
                kickOutBurialId = seat.player.mixConf.get('kickOutBurialId')
                mp.setResult('kickOutBurialId', kickOutBurialId)
                # 首败分享埋点
                mp.rmResult('firstLoseBurialId')
                if seat.player.isFirstLose(ssts[index].isWin):
                    firstLoseBurialId = self.table.room.roomConf.get('firstLoseBurialId')
                    mp.setResult('firstLoseBurialId', firstLoseBurialId)

                # 是否展示交叉导流
                dailyPlayCount = new_table_remote.doGetUserDailyPlayCount(seat.userId, DIZHU_GAMEID)
                mp.setResult('dailyPlay', dailyPlayCount)
                mp.rmResult('showCross')
                mp.setResult('showCross', dailyPlayCount > crossPlayCount)
                mp.setResult('crossDelaySeconds', crossDelaySeconds)
                if ftlog.is_debug():
                    ftlog.debug('sendWinloseRes userId=', seat.userId,
                                'dailyPlayCount=', dailyPlayCount,
                                'showCross=', dailyPlayCount > crossPlayCount,
                                'crossDelaySeconds=', crossDelaySeconds)
                if dailyPlayCount == 3:
                    TGDizhu.getEventBus().publishEvent(ActiveEvent(6, seat.userId, 'playTimes3'))

                mp.rmResult('auth')
                if dailyPlayCount == authPlayCount:
                    mp.setResult('auth', {'auth': 1, 'rewards': rewards})

                # 服务费字段
                mp.setResult('room_fee', ssts[index].fee + ssts[index].fixedFee)

                # 每日首胜
                if seat.player.isFirstWin(ssts[index].isWin):
                    from dizhu.game import TGDizhu
                    from dizhu.entity.common.events import ActiveEvent
                    import poker.util.timestamp as pktimestamp
                    TGDizhu.getEventBus().publishEvent(ActiveEvent(6, seat.userId, 'dailyFirstWin'))
                    today = pktimestamp.formatTimeDayInt()
                    firstWin = {str(today): 1}
                    gamedata.setGameAttrs(seat.userId, DIZHU_GAMEID, ['firstWin'], [strutil.dumps(firstWin)])
                router.sendToUser(mp, seat.userId)


    def buildTableInfoResp(self, seat, isRobot):
        roomConf = seat.player.mixConf
        try:
            if not roomConf:
                ftlog.warn('DizhuTableProtoMix.buildTableInfoResp',
                           'userId=', seat.player.userId,
                           'clientId=', seat.player.clientId,
                           'tableId=', seat.tableId,
                           'seatId=', seat.seatId,
                           'mixId=', seat.player.mixId)
        except:
            pass
        tableConf = roomConf.get('tableConf')
        _, clientVer, _ = strutil.parseClientId(seat.player.clientId)
        mp = self.buildTableMsgRes('table_info')
        playMode = self.table.playMode.name
        if clientVer <= 3.7:
            if playMode == playmodes.PLAYMODE_HAPPY or playMode == playmodes.PLAYMODE_123:
                playMode = 'normal'  # FIX, 客户端happy和123都是normal, grab=1就是欢乐
        mp.setResult('playMode', playMode)
        mp.setResult('isrobot', isRobot)
        mp.setResult('roomLevel', roomConf.get('roomLevel', 1))
        mp.setResult('roomName', roomConf.get('name', ''))
        mp.setResult('isMatch', self.table.room.isMatch)
        mp.setResult('info', self.buildTableBasicInfo())
        mp.setResult('config', self.buildTableBasicConfig(seat.player))
        mp.setResult('stat', self.buildTableStatusInfoForSeat(seat))
        mp.setResult('myCardNote', self.buildTableCardNote(seat))
        mp.setResult('betpoolClose', 1)
        if self.table.gameRound:
            mp.setResult('roundId', self.table.gameRound.roundId)

        _, itemCount = treasurebox.getTreasureRewardItem(self.gameId, seat.player.mixConf.get('roomId') or self.bigRoomId)

        zeroSumFlag = False
        currentBaseScore = seat.player.mixConf.get('tableConf').get('baseScore') or \
        seat.player.mixConf.get('tableConf').get('basebet') * seat.player.mixConf.get('tableConf').get('basemulti') * seat.player.mixConf.get('roomMutil')
        if self.table.room.roomConf.get('zeroSumFlag', 0) == 1:
            zeroSumFlag = True

        for i, tseat in enumerate(self.table.seats):
            seatinfo = self.buildSeatInfo(seat, tseat)
            if tseat.player:
                seatinfo.update(tseat.player.datas)
                # 记牌器数量
                seatinfo['cardNote'] = tseat.player.getCardNoteCount()
                # 当前table的奖券任务奖励
                seatinfo['count'] = itemCount
                # 比赛分
                seatinfo['mscore'] = tseat.player.score
                tseat.player.cleanDataAfterFirstUserInfo()

                # 动态修改金币数量，过滤版本
                if zeroSumFlag:
                    tseatBaseScore = tseat.player.mixConf.get('tableConf').get('baseScore') or \
                                     tseat.player.mixConf.get('tableConf').get('basebet') * tseat.player.mixConf.get('tableConf').get('basemulti') * tseat.player.mixConf.get('roomMutil')
                    tseatBuyinChip = seatinfo['buyinChip']
                    seatinfo['buyinChip'] = int(float(currentBaseScore) / tseatBaseScore * tseatBuyinChip)

            seatinfo['uid'] = tseat.userId
            mp.setResult('seat%s' % (i + 1), seatinfo)

        # 处理记牌器
        if seat.player and seat.player.getCardNoteCount() < 1:
            # 记牌器开启的配置
            cardNoteChip = tableConf.get('cardNoteChip', 0)
            cardNoteDiamod = tableConf.get('cardNoteDiamond', 0)
            cardNote = dizhuconf.getCardNoteTips(seat.player.userId,
                                                 seat.player.chip,
                                                 seat.player.clientId,
                                                 cardNoteChip,
                                                 cardNoteDiamod)
            mp.setResult('cardNote', cardNote)

        if not self.table.room.isMatch:
            player = seat.player
            if player and player.userId:
                # 商品信息 TODO
                mp.setResult('products', tablepay.getProducts(self.gameId, player.userId, seat.player.mixConf.get('roomId') or self.bigRoomId, player.clientId))
                # 互动表情
                emojiConf = emoji.getEmojiConf(self.gameId, seat.player.mixConf.get('roomId') or self.bigRoomId, seat.player.datas.get('vipInfo', {}).get('level', 0))
                if emojiConf:
                    mp.setResult('smiliesConf', emojiConf)

        winstreak = {}
        mixTaskList = self.room.winStreakTask.taskListMap.get(seat.player.mixId)
        playerTask = self.room.winStreakTask.getPlayerTask(seat.player)
        cur = playerTask.progress if playerTask else 0
        if cur >= len(mixTaskList):
            cur = 0
        winstreak['cur'] = cur
        rewards = []

        for task in mixTaskList:
            rewards.append(task.reward)
        winstreak['rewards'] = rewards
        winstreak['imgs'] = self.room.winStreakTask.taskPictures
        mp.setResult('winstreak', winstreak)

        # 房间属于哪个积分榜
        scoreRankingConf = dizhu_score_ranking.getConf()
        rankDef = scoreRankingConf.rankDefineForRoomId(self.bigRoomId)
        if not scoreRankingConf.closed and rankDef and rankDef.switch == 1:
            mp.setResult('scoreboardFlag', rankDef.rankId)

        taskInfo = task_remote.getNewbieTaskInfo(DIZHU_GAMEID, seat.userId, seat.player.playShare.totalCount)
        if taskInfo is not None:
            mp.setResult('newertask', taskInfo)

        winSteakBuff, loseStreakBuff = dizhu_giftbag.checkUserGiftBuff(seat.player.userId)
        if winSteakBuff:
            mp.setResult('buff', 'winSteakBuff')
        elif loseStreakBuff:
            mp.setResult('buff', 'loseStreakBuff')

        dailyPlayCount = new_table_remote.doGetUserDailyPlayCount(seat.userId, DIZHU_GAMEID)
        mp.setResult('dailyPlay', dailyPlayCount)
        if ftlog.is_debug():
            ftlog.debug('dizhu.mix.tableproto.buildTableInfoResp.checkUserGiftBuff',
                        'winSteakBuff=', winSteakBuff,
                        'loseStreakBuff=', loseStreakBuff,
                        'mp=', mp)
        return mp

    def buildGameStartResForSeat(self, seat):
        mp = self.buildTableMsgRes('table_call', 'game_start')
        mp.setResult('stat', self.buildTableStatusInfoForSeat(seat))
        seatTBBoxInfoList = []
        for tseat in self.table.seats:
            if tseat.player:
                itemId, itemCount = treasurebox.getTreasureRewardItem(self.gameId, tseat.player.mixConf.get('roomId'))
                if itemId:
                    itemId = hallconf.translateAssetKindIdToOld(itemId)
                tempTbc = tseat.player.datas.get('tbc', 0)
                tempTbt = tseat.player.datas.get('tbt', 0)
                seatTBBoxInfoList.append({'tbc':tempTbc,
                                          'tbt': tempTbt,
                                          'item':itemId,
                                          'count':itemCount
                                          })

        mp.setResult('seattb', seatTBBoxInfoList)
        mp.setResult('myCardNote', self.buildTableCardNote(seat))
        return mp

    def buildTableBasicConfig(self, player, zeroSumFlag=0):
        '''
        原table.buildBasicInfo中的config数据
        '''
        if not player.mixId:
            raise Exception('')

        tableConf = player.mixConf.get('tableConf', {})

        # 宝箱信息
        tbbox, couponrule = treasurebox.getTreasureTableTip(self.gameId, player.mixConf.get('roomId'))

        # 配置信息
        config = {}
        config['tbbox'] = tbbox
        config['couponrule'] = couponrule

        config['maxseat'] = tableConf.get('maxSeatN')
        config['rangpaiMultiType'] = tableConf.get('rangpaiMultiType')
        config['autoChange'] = tableConf.get('autochange')
        config['base'] = tableConf.get('basebet')
        config['basemulti'] = tableConf.get('basemulti')
        config['gslam'] = tableConf.get('gslam')
        config['grab'] = tableConf.get('grab')
        config['chat'] = tableConf.get('canchat')
        config['cardNote'] = self.table.runConf.cardNote
        config['optime'] = tableConf.get('optimeOutCard')
        config['coin2chip'] = tableConf.get('coin2chip')
        config['lucky'] = tableConf.get('lucky')
        config['untiCheat'] = tableConf.get('unticheat')
        config['passtime'] = tableConf.get('passtime')
        config['mixShowChip'] = tableConf.get('mixShowChip')

        config['isMingPai'] = self.table.runConf.showCard
        config['roommulti'] = player.mixConf.get('roomMutil')
        config['maxcoin'] = player.mixConf.get('maxCoin')
        config['mincoin'] = player.mixConf.get('minCoin')
        config['sfee'] = player.mixConf.get('roomFee')
        config['optime'] = tableConf.get('optime')
        config['matchInfo'] = ''  # 老版本数据结构兼容
        config['autoPlay'] = self.table.runConf.autoPlay
        config['canQuit'] = self.table.runConf.canQuit
        config['winCoinLimit'] = tableConf.get('winCoinLimit', 0)

        # 小于3.7版本是否能够聊天、防作弊统一使用的是untiCheat字段
        # 对于小于3.7版本的在不防作弊但是不能聊天时处理为防作弊
        _, clientVer, _ = strutil.parseClientId(player.clientId)
        if clientVer and clientVer < 3.7:
            if not config['chat'] and not config['untiCheat']:
                config['untiCheat'] = 1
        return config

    def buildQuickStartResp(self, seat, isOK, reason):
        mp = self.buildTableMsgRes('quick_start')
        mp.setResult('mixId', seat.player.mixId)
        mp.setResult('isOK', isOK)
        mp.setResult('seatId', seat.seatId)
        mp.setResult('reason', reason)
        return mp

    def sendTableChatRes(self, seat, isFace, voiceIdx, chatMsg):
        # 如果是农民，只能地主收到聊天信息
        for tseat in self.table.seats:
            if tseat.player and not seat.isGiveup:
                if tseat.userId != seat.userId:
                    if isFace != 1 and seat.player.mixConf.get('tableConf', {}).get('chatCheat', 0) and self.table.gameRound and seat != self.table.gameRound.dizhuSeat and tseat != self.table.gameRound.dizhuSeat:
                        continue
                    chatMsg = bug_fix._bugFixFilterChatMsgForPNG(tseat.player.clientId, chatMsg)
                mp = self.buildTableChatRes(seat, isFace, voiceIdx, chatMsg)
                router.sendToUser(mp, tseat.userId)
