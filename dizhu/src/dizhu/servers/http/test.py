# -*- coding=utf-8 -*-
'''
Created on 2015年5月7日

@author: zqh
'''

from sre_compile import isstring
import time
import functools
from datetime import datetime

from dizhu.activities.betguess import ActivityModel, IssueCalculator, \
    UserRecorder
from dizhu.activities.ddzfund import UserPlayDataDatabase
from dizhu.activities.toolbox import Tool, UserInfo
from dizhu.activities_wx.activity_wx_active import ActivityWxUserActive
from dizhu.entity import tableskin, dizhupopwnd, dizhu_score_ranking, dizhu_util, dizhu_new_roundlist, dizhu_signin
from dizhu.entity.dizhuconf import DIZHU_GAMEID
from dizhu.entity.dizhufishing import FishHelper
from dizhu.entity.tableskin import MySkinModel
from dizhu.entity.led_util import LedUtil
from dizhu.gamecards.sendcard import SendCardPolicyUserId
from dizhu.gametable.dizhu_seat import tdz_seat_title
from dizhu.gametable.dizhu_state import tdz_stat_title, tdz_stat_title2
from dizhu.replay import replay_service
from dizhu.servers.util.ft_handler import FTHandler
from dizhu.servers.util.replay_handler import DizhuReplayHandler
from dizhu.servers.util.rpc import new_table_remote
from dizhu.servers.util.rpc import task_remote, table_remote, \
    act_betguess_remote, event_remote
from dizhu.servers.util.score_ranklist_handler import ScoreRankingHandler
from dizhu.servers.util.tableskin_handler import TableSkinTcpHandler
from dizhu.entity import dizhuled
from freetime.core.timer import FTTimer
from freetime.entity.msg import MsgPack
from freetime.support.tcpagent import wrapper
import freetime.util.log as ftlog
from hall.entity import hallpopwnd
from hall.entity.hallactivity.activity import TYActivityDaoImpl
from hall.game import TGHall
from hall.servers.common.base_http_checker import BaseHttpMsgChecker
from poker.entity.biz.content import TYContentItem
from poker.entity.configure import gdata, configure
from poker.entity.dao import gamedata, sessiondata, daobase
from poker.entity.events.tyevent import ChargeNotifyEvent, EventUserLogin
from poker.protocol import runhttp, router
from poker.protocol.decorator import markHttpHandler, markHttpMethod
from poker.util import strutil
import poker.util.timestamp as pktimestamp


@markHttpHandler
class TestDiZhuHttpHandler(BaseHttpMsgChecker):


    def __init__(self):
        pass


    def isEnable(self):
        return gdata.enableTestHtml()

    def _check_param_nowTime(self, key, params):
        dtstr = runhttp.getParamStr(key)
        try:
            if not dtstr:
                return None, None
            dt = datetime.strptime(dtstr, '%Y-%m-%d %H:%M:%S')
            return None, pktimestamp.datetime2Timestamp(dt)
        except:
            return 'param nowTime error', dtstr


    #########score_rank_list##########
    def _check_param_issn(self, key, params):
        progress = runhttp.getParamStr(key, 0)
        return None, progress

    def _check_param_timeStampStr(self, key, params):
        progress = runhttp.getParamStr(key, '')
        return None, progress

    def _check_param_adId(self, key, params):
        adId = runhttp.getParamStr(key, '')
        return None, adId

    def _check_param_score(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_roundCount(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_isdibao(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_winStreak(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_chipDelta(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_rankId(self, key, params):
        progress = runhttp.getParamStr(key, '0')
        return None, progress

    def _check_param_rank(self, key, params):
        progress = runhttp.getParamInt(key)
        return None, progress

    def _check_param_baitId(self, key, params):
        baitId = runhttp.getParamInt(key)
        return None, baitId

    def _check_param_playCount(self, key, params):
        value = runhttp.getParamInt(key)
        return None, value

    def _check_param_bigRoomId(self, key, params):
        value = runhttp.getParamInt(key)
        return None, value

    def _check_param_dibaoStu(self, key, params):
        value = runhttp.getParamInt(key, 0)
        if (value is not None
            and value not in (0,1,2)):
            return 'param dibaoStu error', value
        return None, value

    def _check_param_rstu(self, key, params):
        value = runhttp.getParamInt(key, 0)
        if (value is not None
            and value not in (0,1,2)):
            return 'param rankRewardState error', value
        return None, value

    def _check_param_name(self, key, params):
        value = runhttp.getParamStr(key, '')
        return None, value

    def _check_param_purl(self, key, params):
        value = runhttp.getParamStr(key, '')
        return None, value

    def _check_param_begin(self, key, params):
        value = runhttp.getParamInt(key)
        return None, value

    def _check_param_end(self, key, params):
        value = runhttp.getParamInt(key)
        return None, value

    def _check_param_userId(self, key, params):
        value = runhttp.getParamInt(key)
        return None , value

    #playCount, dibaoStu, rstu, rank, name, purl
    #########score_rank_list##########

    def _check_param_progress(self, key, params):
        progress = runhttp.getParamInt(key, 0)
        if not isinstance(progress, int):
            return 'param progress error', None
        return None, progress

    def _check_param_curSkinId(self, key, params):
        curSkinId = runhttp.getParamStr(key)
        if not isstring(curSkinId):
            return 'param curSkinId error', None
        return None, curSkinId

    def _check_param_mySkinIds(self, key, params):
        mySkinIds = runhttp.getParamStr(key)
        if not isstring(mySkinIds):
            return 'param skinId error', None
        skinIds = mySkinIds.split(',')
        return None, skinIds

    def _check_param_skinId(self, key, params):
        skinId = runhttp.getParamStr(key)
        if not isstring(skinId):
            return 'param skinId error', None
        return None, skinId

    def _check_param_taskId(self, key, params):
        taskId = runhttp.getParamInt(key, 0)
        if not isinstance(taskId, int):
            return 'param taskId error', None
        return None, taskId

    def _check_param_isTip(self, key, params):
        isTip = runhttp.getParamInt(key, 0)
        if not isinstance(isTip, int):
            return 'param isTip error', None
        return None, isTip

    def _check_param_isauto(self, key, params):
        isauto = runhttp.getParamInt(key, 0)
        if not isinstance(isauto, int):
            return 'param isauto error', None
        return None, isauto

    def _check_param_seatId(self, key, params):
        seatId = runhttp.getParamInt(key, 0)
        if not isinstance(seatId, int):
            return 'param seatId error', None
        return None, seatId

    def _check_param_version(self, key, params):
        version = runhttp.getParamInt(key, 0)
        if not isinstance(version, int):
            return 'param version error', None
        return None, version

    def _check_param_taskIdList(self, key, params):
        try:
            jstr = runhttp.getParamStr(key)
            taskIdList = jstr.split(',')
            ret = []
            for taskId in taskIdList:
                ret.append(int(taskId))
            return None, ret
        except:
            return 'the jsonstr params is not a list Format !!', None

    def _check_param_videoIdList(self, key, params):
        try:
            jstr = runhttp.getParamStr(key)
            videoIdList = jstr.split(',')
            ret = []
            for videoId in videoIdList:
                videoId = videoId.strip()
                ret.append(videoId)
            return None, ret
        except:
            return 'Error param videoIdList !!', None

    def _check_param_userCardList(self, key, params):
        try:
            jstr = runhttp.getParamStr(key)
            return None, self.decodeCardList(jstr)
        except:
            return 'the userCardList is not a list Format !!', None

    def decodeCardList(self, cardListStr):
        ret = []
        if cardListStr:
            cardList = cardListStr.split(',')
            for c in cardList:
                ret.append(int(c))
        return ret

    def _check_param_baseCardList(self, key, params):
        try:
            jstr = runhttp.getParamStr(key)
            return None, self.decodeCardList(jstr)
        except:
            return 'the baseCardList is not a list Format !!', None

    def _check_param_jsondata(self, key, params):
        jstr = runhttp.getParamStr(key)
        jdata = strutil.loads(jstr, ignoreException=True)
        if jdata :
            return None, jdata
        return 'the jsonstr params is not a JSON Format !!', None

    def _check_param_roomId(self, key, params):
        roomId = runhttp.getParamInt(key, -1)
        if isinstance(roomId, int) and roomId >= 0:
            return None, roomId
        return None, 0

    def _check_param_clientRoomId(self, key, params):
        clientRoomId = runhttp.getParamInt(key, -1)
        if isinstance(clientRoomId, int) and clientRoomId >= 0:
            return None, clientRoomId
        return None, 0

    def _check_param_count(self, key, params):
        count = runhttp.getParamInt(key, -1)
        if isinstance(count, int) and count > 0:
            return None, count
        return 'the count must > 0', None

    def _check_param_roundId(self, key, params):
        roundId = runhttp.getParamStr(key, '')
        if not roundId:
            return 'param roundId error', None
        return None, roundId

    def _check_param_issueNum(self, key, params):
        issueNum = runhttp.getParamStr(key, '')
        if not issueNum:
            issueNum = replay_service.getIssueNumber(pktimestamp.getCurrentTimestamp() - 86400)
        return None, issueNum

    def _check_param_videoId(self, key, params):
        videoId = runhttp.getParamStr(key, '')
        if not videoId:
            return 'param videoId error', None
        return None, videoId

    def _check_param_shareType(self, key, params):
        shareType = runhttp.getParamStr(key, '')
        if not shareType:
            return 'param shareType error', None
        return None, shareType

    def _check_param_tableId(self, key, params):
        tableId = runhttp.getParamInt(key, 0)
        if tableId <= 0:
            return 'param roundId error', None
        return None, tableId

    def _check_param_nRound(self, key, params):
        nRound = runhttp.getParamInt(key, 0)
        if not isinstance(nRound, int) or nRound <= 0:
            return 'param nRound error', None
        return None, nRound

    def _check_param_canDouble(self, key, params):
        canDouble = runhttp.getParamInt(key, 0)
        if canDouble not in (0, 1):
            return 'param canDouble error', None
        return None, canDouble

    def _check_param_playMode(self, key, params):
        playMode = runhttp.getParamStr(key, '')
        if not playMode:
            return 'param playMode error', None
        return None, playMode

    def _check_param_ftId(self, key, params):
        ftId = runhttp.getParamStr(key, '')
        if not ftId:
            return 'param ftId error', None
        return None, ftId

    def _check_param_userName(self, key, params):
        userName = runhttp.getParamStr(key, '')
        if not userName:
            return 'param userName error', None
        return None, userName

    def _check_param_roomName(self, key, params):
        roomName = runhttp.getParamStr(key, '')
        if not roomName:
            return 'param roomNam error', None
        return None, roomName

    def _check_param_reward(self, key, params):
        reward = runhttp.getParamStr(key, '')
        if not reward:
            return 'param reward error', None
        return None, reward

    def _check_param_issue(self, key, params):
        issue = runhttp.getParamStr(key, '')
        return None, issue

    def _check_param_start(self, key, params):
        start = runhttp.getParamInt(key, 0)
        return None, start

    def _check_param_stop(self, key, params):
        stop = runhttp.getParamInt(key, -1)
        return None, stop

    def _check_param_preIssue(self, key, params):
        preIssue = runhttp.getParamStr(key)
        return None, preIssue

    def _check_param_segment(self, key, params):
        segment = runhttp.getParamInt(key)
        return None, segment

    def _check_param_stars(self, key, params):
        stars = runhttp.getParamInt(key)
        return None, stars

    def _check_param_totalStars(self, key, params):
        totalStars = runhttp.getParamInt(key)
        return None, totalStars

    def _check_param_state(self, key, params):
        state = runhttp.getParamInt(key)
        return None, state

    def _check_param_inherit(self, key, params):
        inherit = runhttp.getParamInt(key)
        return None, inherit

    def _check_param_dayNumber(self, key, params):
        dayNumber = runhttp.getParamInt(key)
        if isinstance(dayNumber, int):
            return None, dayNumber
        return 'ERROR of dayNumber !', None

    def _check_param_itemId(self, key, params):
        itemId = runhttp.getParamStr(key, '')
        if not itemId:
            return 'param itemId error', None
        return None, itemId

    def _check_param_assetCount(self, key, params):
        assetCount = runhttp.getParamInt(key)
        if isinstance(assetCount, int):
            return None, assetCount
        return 'ERROR of assetCount !', None

    def _check_param_scheduleId(self, key, params):
        scheduleId = runhttp.getParamInt(key)
        if isinstance(scheduleId, int):
            return None, scheduleId
        return 'ERROR of scheduleId !', None

    def _check_param_rewardKind(self, key, params):
        rewardKind = runhttp.getParamStr(key, '')
        if not rewardKind:
            return 'param rewardKind error', None
        return None, rewardKind

    def _check_param_day(self, key, params):
        day = runhttp.getParamInt(key)
        if isinstance(day, int):
            return None, day
        return 'ERROR of day !', None

    def _check_param_typeId(self, key, params):
        typeId = runhttp.getParamInt(key)
        if isinstance(typeId, int):
            return None, typeId
        return 'ERROR of typeId !', None

    def makeErrorResponse(self, ec=-1, message=None):
        return {'error':{'ec':ec, 'message':message}}


    def makeResponse(self, result):
        return {'result':result}

    @markHttpMethod(httppath='/gtest/dizhu/robotcallmatch')
    def doTestRobotCallMatch(self, roomId, count):
        ftlog.info('doTestRobotCallMatch start roomId=', roomId, 'count=', count)
        mo = MsgPack()
        mo.setCmd('robotmgr')
        mo.setParam('action', 'callmatch')
        mo.setParam('gameId', 6)
        mo.setParam('roomId', roomId)
        mo.setParam('robotCount', count)
        router.sendRobotServer(mo)

    @markHttpMethod(httppath='/gtest/dizhu/robotcallup')
    def doTestRobotCallUp(self, roomId0, tableId0):
        ftlog.info('doTestRobotCallUp start roomId=', roomId0, 'tableId=', tableId0)
        smsg = MsgPack()
        smsg.setCmd('robotmgr')
        smsg.setParam('action', 'callup')
        smsg.setParam('gameId', 6)
        smsg.setParam('roomId', roomId0)
        smsg.setParam('tableId', tableId0)
        smsg.setParam('userCount', 1)
        smsg.setParam('seatCount', 3)
        smsg.setParam('users', [0, 0, 0])
        smsg = smsg.pack()

        msg = MsgPack()
        msg.setParam('serverids', ['RB001'])
        msg.setParam('sendmessage', smsg)
        msg.setParam('userheader1', '')
        msg.setParam('userheader2', '')
        msg.setParam('timeout', 3)
        msg = msg.pack()
        pdatas = {'msgpack' : msg}
        ftlog.info('doTestRobotCallUp smsg=', smsg, 'pdatas=', pdatas)
        wrapper.send('RB001', smsg, '', '')
        return self.makeResponse('OK')

    @markHttpMethod(httppath='/gtest/dizhu/winlose')
    def doTestDiZhuWinLose(self, jsondata):
        ftlog.info('doTestDiZhuWinLose->', jsondata)
        try:
            roomId = jsondata['roomId']
            tableId = jsondata['tableId']
            roundNum = jsondata['roundNum']
            winSeatId = jsondata['winSeatId']
            roomId = jsondata['roomId']
            tableConf_ = jsondata['tableConf_']
            tableStatus_ = []
            datas = jsondata['tableStatus_']
            ttitle = tdz_stat_title + tdz_stat_title2
            for x in  ttitle :
                tableStatus_.append(datas[x])
            tableStatus_.append(None)  # 差一个validCard位置
            tableSeats_ = []
            datas = jsondata['tableSeats_']
            for data in datas :
                seat = []
                for x in tdz_seat_title :
                    seat.append(data[x])
                tableSeats_.append(seat)
            tablePlayers_ = jsondata['tablePlayers_']
            result = table_remote.doTableWinLose(roomId, tableId, roundNum,
                                                                 winSeatId, tableConf_, tableStatus_,
                                                                 tableSeats_, tablePlayers_)
            return self.makeResponse(result)
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ttask/setTasks')
    def doTTaskSetTasks(self, userId, taskIdList):
        try:
            ftlog.info('doTTaskSetTasks userId=', userId,
                       'taskIdList=', taskIdList)
            newTaskIdList = task_remote.setTableTasks(6, userId, taskIdList)
            return self.makeResponse({'taskIdList':newTaskIdList})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ttask/setProgress')
    def doTTaskSetProgress(self, userId, taskId, progress):
        try:
            ftlog.info('doTTaskSetProgress userId=', userId,
                       'taskId=', taskId,
                       'progress=', progress)
            changed, finishCount, newProgress = task_remote.setTableTaskProgress(6, userId, taskId, progress)
            return self.makeResponse({'changed':changed, 'finishCount':finishCount, 'progress':newProgress})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ttask/setProgressHack')
    def doTTaskSetProgressHack(self, userId, taskId, progress):
        try:
            ftlog.info('doTTaskSetProgressHack userId=', userId,
                       'taskId=', taskId,
                       'progress=', progress)
            newProgress = task_remote.setTableTaskProgressHack(6, userId, taskId, progress)
            return self.makeResponse({'progress':newProgress})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ttask/getReward')
    def doTTaskGetReward(self, userId, taskId):
        try:
            ftlog.info('doTTaskGetReward userId=', userId,
                       'taskId=', taskId)
            rewardString = task_remote.getTableTaskReward(6, userId, taskId)
            return self.makeResponse({'reward':rewardString})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ttask/getTasks')
    def doTTaskGetTasks(self, userId, taskId):
        try:
            ftlog.info('doTestSetTableTask userId=', userId,
                       'taskId=', taskId)
            tasks = task_remote.getTableTasks(6, userId)
            return self.makeResponse({'tasks':tasks})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    def _encodeCardList(self, cardList):
        cards = []
        for c in cardList:
            cards.append(str(c))
        return cards

    @markHttpMethod(httppath='/gtest/dizhu/cards/set')
    def doCardsSet(self, userId, userCardList, baseCardList):
        ftlog.info('doCardsSet userId=', userId,
                   'userCardList=', userCardList,
                   'baseCardList=', baseCardList)

        if userCardList:
            gamedata.setGameAttr(userId, 6, 'test.cards', ','.join(self._encodeCardList(userCardList)))
        if baseCardList:
            gamedata.setGameAttr(userId, 6, 'test.bcards', ','.join(self._encodeCardList(baseCardList)))
        return self.makeResponse({'cardList':userCardList, 'baseCardList':baseCardList})

    @markHttpMethod(httppath='/gtest/dizhu/cards/get')
    def doCardsGet(self, userId, userCardList, baseCardList):
        ftlog.info('doCardsGet userId=', userId)

        userCardList = self.decodeCardList(gamedata.getGameAttr(userId, 6, 'test.cards'))
        baseCardList = self.decodeCardList(gamedata.getGameAttr(userId, 6, 'test.bcards'))
        return self.makeResponse({'cardList':userCardList, 'baseCardList':baseCardList})

    @markHttpMethod(httppath='/gtest/dizhu/cards/clear')
    def doCardsClear(self, userId):
        ftlog.info('doCardsClear userId=', userId)

        gamedata.delGameAttr(userId, 6, 'test.cards')
        gamedata.delGameAttr(userId, 6, 'test.bcards')
        return self.makeResponse({'cardList':[], 'baseCardList':[]})

    @markHttpMethod(httppath='/gtest/dizhu/cards/send')
    def doCardsSend(self, userId):
        ftlog.info('doCardsSend userId=', userId)
        cards = SendCardPolicyUserId.getInstance().sendCards(601, [userId, 100, 101])
        return self.makeResponse({'cards':cards})

    @markHttpMethod(httppath='/gtest/dizhu/dtask/getTasks')
    def doDTaskGetTasks(self, userId):
        try:
            ftlog.info('doDTaskGetTasks userId=', userId)
            tasks = task_remote.getDailyTasks(6, userId)
            return self.makeResponse({'tasks':tasks})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/dtask/setProgress')
    def doDTaskSetProgress(self, userId, taskId, progress):
        try:
            ftlog.info('doDTaskSetProgress userId=', userId,
                       'taskId=', taskId,
                       'progress=', progress)
            changed, finishCount, newProgress = task_remote.setDailyTaskProgress(6, userId, taskId, progress)
            return self.makeResponse({'changed':changed, 'finishCount':finishCount, 'progress':newProgress})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/dtask/getReward')
    def doDTaskGetReward(self, userId, taskId):
        try:
            ftlog.info('doDTaskGetReward userId=', userId,
                       'taskId=', taskId)
            rewardString = task_remote.getDailyTaskReward(6, userId, taskId)
            return self.makeResponse({'reward':rewardString})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/dtask/refresh')
    def doDTaskRefresh(self, userId, taskId):
        try:
            ftlog.info('doDTaskRefresh userId=', userId,
                       'taskId=', taskId)
            tasks = task_remote.refreshDailyTasks(6, userId)
            return self.makeResponse({'tasks':tasks})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/loseout')
    def doLosout(self, userId, roomId):
        try:
            ftlog.info('doDTaskRefresh userId=', userId,
                       'roomId=', roomId)
            clientId = sessiondata.getClientId(userId)
            _, ver, _ = strutil.parseClientId(clientId)
            if ver == 3.502:
                mo = table_remote.processLoseOutRoom(6, userId, clientId, roomId)
            else:
                mo = hallpopwnd.processLoseOutRoomV3_7(6, userId, clientId, roomId)
            return self.makeResponse({'result':mo._ht})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), '有异常')

    @markHttpMethod(httppath='/gtest/dizhu/charge')
    def doCharge(self, userId, gameId):
        ftlog.info('doCharge userId=', userId)
        money = runhttp.getParamInt('money')
        chargeEvent = ChargeNotifyEvent(userId, gameId, money, 0, 0, 'test')
        TGHall.getEventBus().publishEvent(chargeEvent)
        return self.makeResponse({'result':'ok', 'money': money, 'gameId':gameId})

    @markHttpMethod(httppath='/gtest/dizhu/act/fund')
    def doActivityFund(self, userId):
        ftlog.info('doActivityFund userId=', userId)

        roomId = runhttp.getParamInt('roomId')
        data_wrapper = UserPlayDataDatabase(userId)
        data_wrapper.increase(True, False, 0, roomId)
        data = data_wrapper._readFromReids()

        return self.makeResponse({'result':'ok', 'key': data_wrapper.getkey(), 'data': data})

    @markHttpMethod(httppath='/gtest/dizhu/replay/getTopnInfo')
    def doReplayGetTopnInfo(self, videoId):
        issueNum, count = replay_service.getTopnInfo(videoId)
        return self.makeResponse({'result':'ok', 'lastTopnDate':issueNum, 'topnCount':count})

    @markHttpMethod(httppath='/gtest/dizhu/replay/setTopnInfo')
    def doReplaySetTopnInfo(self, videoId, issueNum, count):
        replay_service.setTopnInfo(videoId, issueNum, count)
        return self.doReplayGetTopnInfo(videoId)

    @markHttpMethod(httppath='/gtest/dizhu/replay/save')
    def doReplaySave(self, userId, roomId, tableId, roundId):
        mo = MsgPack()
        mo.setCmd('table')
        mo.setParam('action', 'replay_save')
        mo.setParam('userId', userId)
        mo.setParam('gameId', 6)
        mo.setParam('roomId', roomId)
        mo.setParam('tableId', tableId)
        mo.setParam('roundId', roundId)
        router.queryTableServer(mo, roomId)
        return self.makeResponse('ok')

    @markHttpMethod(httppath='/gtest/dizhu/replay/remove')
    def doReplayRemove(self, userId, videoId):
        return DizhuReplayHandler._doMineRem(userId, 6, sessiondata.getClientId(userId), videoId)

    @markHttpMethod(httppath='/gtest/dizhu/replay/wonderful/list')
    def doReplayListWonderful(self, userId, issueNum):
        return DizhuReplayHandler._doListWonderful(userId, 6, sessiondata.getClientId(userId), issueNum)

    @markHttpMethod(httppath='/gtest/dizhu/replay/getTop')
    def doReplayGetTop(self, issueNum):
        replays = replay_service.getTopNReplay(issueNum, replay_service._maxTop)
        videos = DizhuReplayHandler.encodeReplaysForWonderful(0, replays)
        return {'videos':videos}

    @markHttpMethod(httppath='/gtest/dizhu/replay/removeTop')
    def doReplayRemoveTop(self, issueNum, videoId):
        n = replay_service.removeFromTopn(issueNum, videoId)
        return {'removeCount':n}

    @markHttpMethod(httppath='/gtest/dizhu/replay/mine/list')
    def doReplayListMine(self, userId):
        return DizhuReplayHandler._doListMine(userId, 6, sessiondata.getClientId(userId))

    @markHttpMethod(httppath='/gtest/dizhu/replay/view')
    def doReplayView(self, userId, videoId, issueNum):
        timestamp = pktimestamp.timestrToTimestamp(issueNum, '%Y%m%d')
        return DizhuReplayHandler._doView(userId, 6, sessiondata.getClientId(userId), videoId, timestamp)

    @markHttpMethod(httppath='/gtest/dizhu/replay/like')
    def doReplayLike(self, userId, videoId):
        return DizhuReplayHandler._doLike(userId, 6, sessiondata.getClientId(userId), videoId)

    @markHttpMethod(httppath='/gtest/dizhu/replay/cleanupTip')
    def doCleanupTip(self, userId):
        return DizhuReplayHandler._doMineCleanupTip(userId, 6, sessiondata.getClientId(userId))

    @markHttpMethod(httppath='/gtest/dizhu/replay/share')
    def doReplayShare(self, userId, videoId, shareType):
        return DizhuReplayHandler._doShare(userId, 6, sessiondata.getClientId(userId), videoId, shareType)

    @markHttpMethod(httppath='/gtest/dizhu/replay/getManualTopN')
    def doReplayGetManualTopN(self):
        topn = replay_service.getManualTopN(10)
        return {'topn':topn}

    @markHttpMethod(httppath='/gtest/dizhu/replay/setManualTopN')
    def doReplaySetManualTopN(self, videoIdList):
        replay_service.setManualTopN(videoIdList)
        topn = replay_service.getManualTopN(10)
        return {'topn':topn}

    @markHttpMethod(httppath='/gtest/dizhu/ft/getConf')
    def doFTGetConf(self, userId):
        msg = FTHandler._doFTGetConf(userId, DIZHU_GAMEID, sessiondata.getClientId(userId))
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/ft/create')
    def doFTCreate(self, userId, nRound, canDouble, playMode):
        msg = FTHandler._doFTCreate(userId, DIZHU_GAMEID, sessiondata.getClientId(userId),
                                    {'nRound':nRound,
                                     'double':canDouble,
                                     'playMode':playMode})
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/ft/enter')
    def doFTEnter(self, userId, ftId):
        msg = FTHandler._doFTEnter(userId, DIZHU_GAMEID, sessiondata.getClientId(userId), ftId)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/act/betguess/userbet')
    def doActivityBetguessUserBet(self):
        '''
        @param activityGameId: 6(配置里配置的哪个GameId就填哪个GameId)
        @param activityId: 活动ID
        @param issueNumber: '2016-10-31 18:20:00'
        @param userId: userId
        @param betChip: 下注金币
        @param isLeft: 0(False),1(True)
        '''
        try:
            activityGameId = runhttp.getParamInt('activityGameId')
            activityId = runhttp.getParamStr('activityId')
            issueNumber = runhttp.getParamStr('issueNumber')
            userId = runhttp.getParamInt('userId')
            betChip = runhttp.getParamInt('betChip')
            isLeft = runhttp.getParamInt('isLeft')
            if activityGameId == None or \
                activityId == None or \
                issueNumber == None or \
                userId == None or \
                betChip == None or \
                isLeft == None:
                return self.makeErrorResponse(-1, 'params error').pack()

            ftlog.debug('BetguessHttpHandler.doActivityBetguessUserBet',
                        'userId=', userId,
                        'betChip=', betChip,
                        'isLeft=', isLeft,
                        'activityGameId=', activityGameId,
                        'activityId=', activityId,
                        'issueNumber=', issueNumber)

            err, ret = act_betguess_remote.userBet(userId, betChip, isLeft == 1, issueNumber, activityId)
            if err:
                return self.makeErrorResponse(-1, err).pack()

            activityModel = ActivityModel.loadModel(activityGameId, activityId, issueNumber)
            response = MsgPack()
            response.setResult("activityModel", activityModel.__dict__)
            response.setResult("activityData", ret)
            return response.pack()
        except:
            ftlog.error()
            return self.makeErrorResponse().pack()

    @markHttpMethod(httppath='/gtest/dizhu/act/betguess/query')
    def doActivityBetguessQuery(self):
        '''
        @param activityGameId: 6(配置里配置的哪个GameId就填哪个GameId)
        @param activityId: 活动ID
        @param issueNumber: '2016-10-31 18:20:00'
        '''
        try:
            activityGameId = runhttp.getParamInt('activityGameId')
            activityId = runhttp.getParamStr('activityId')
            issueNumber = runhttp.getParamStr('issueNumber')
            if activityGameId == None or \
                activityId == None or \
                issueNumber == None:
                return self.makeErrorResponse(-1, 'params error').pack()

            ftlog.debug('BetguessHttpHandler.doActivityBetguessQuery',
                        'activityGameId=', activityGameId,
                        'activityId=', activityId,
                        'issueNumber=', issueNumber)

            activityModel = ActivityModel.loadModel(activityGameId, activityId, issueNumber)

            err, issueMap = self.getActivityIssueMapConf(activityId)
            if err:
                return err

            issueCalculator = IssueCalculator(issueMap)
            issueConf = issueCalculator.getCurrentIssueConf(issueNumber)
            if (issueNumber not in issueMap) or (not issueConf):
                return self.makeErrorResponse(-1, 'issueNumber not found! issueNumber maybe error').pack()

            bankerPumping = issueConf.get('bankerPumping', 0)
            # 奖池为抽水金额
            totalChip = activityModel.countChipLeft + activityModel.countChipRight
            # 奖池金额
            betPoolChip = int((activityModel.countChipLeft + activityModel.countChipRight) * (1 - bankerPumping))
            # 左赔率
            leftBetOdds = betPoolChip / activityModel.countChipLeft if activityModel.countChipLeft > 0 else 0
            # 右赔率
            rightBetOdds = betPoolChip / activityModel.countChipRight if activityModel.countChipRight > 0 else 0

            response = MsgPack()
            response.setResult('totalChip', totalChip)
            response.setResult('betPoolChip', betPoolChip)
            response.setResult('leftBetOdds', leftBetOdds)
            response.setResult('rightBetOdds', rightBetOdds)
            response.setResult('bankerPumping', bankerPumping)
            response.setResult('countChipLeft', activityModel.countChipLeft)
            response.setResult('countChipRight', activityModel.countChipRight)
            response.setResult('resultState', activityModel.resultState)

            response.setResult("activityModel", activityModel.__dict__)
            response.setResult('pastIssueNumberList', issueCalculator.getAlreadyPastIssueNumberList())
            return response.pack()
        except:
            ftlog.error()
            return self.makeErrorResponse().pack()


    @markHttpMethod(httppath='/gtest/dizhu/act/betguess/setresult')
    def doActivityBetguessSetResult(self):
        '''
        @param activityGameId: 6(配置里配置的哪个GameId就填哪个GameId)
        @param activityId: 活动ID
        @param issueNumber: '2016-10-31 18:20:00'
        @param resultState: 0,1,2
        '''
        try:
            activityGameId = runhttp.getParamInt('activityGameId')
            activityId = runhttp.getParamStr('activityId')
            issueNumber = runhttp.getParamStr('issueNumber')
            resultState = runhttp.getParamInt('resultState')
            if activityGameId == None or \
                activityId == None or \
                issueNumber == None or \
                resultState == None:
                return self.makeErrorResponse(-1, 'params error').pack()

            ftlog.debug('BetguessHttpHandler.doActivityBetguessSetResult',
                        'activityGameId=', activityGameId,
                        'activityId=', activityId,
                        'issueNumber=', issueNumber,
                        'resultState=', resultState)

            err, issueMap = self.getActivityIssueMapConf(activityId)
            if err:
                return err

            # 验证issueNumber是否存在
            if issueNumber not in issueMap:
                return self.makeErrorResponse(-1, 'issueNumber not found! issueNumber maybe error').pack()

            # 给活动设置竞猜结果
            if not ActivityModel.updateResult(activityGameId, activityId, issueNumber, resultState):
                return self.makeErrorResponse(-1, 'result set failed! resultState maybe error').pack()

            # 获得最新的活动数据
            activityModel = ActivityModel.loadModel(activityGameId, activityId, issueNumber)
            if activityModel.resultState == activityModel.RESULT_STATE_NONE:
                return self.makeErrorResponse(-1, 'activityModel.resultState not set!').pack()

            # 遍历参与玩家
            chipCounter = 0
            userIdList = UserRecorder.getUsers(activityGameId, activityId, issueNumber)
            for userId in userIdList:
                response = act_betguess_remote.sendRewards(userId,
                                                        activityModel.countChipLeft, activityModel.countChipRight, activityModel.resultState,
                                                        activityGameId, activityId, issueNumber)
                if response.get('err'):
                    return self.makeErrorResponse(-1, response.get('err')).pack()
                chipCounter += response.get('chip', 0)

            activityModel = ActivityModel.loadModel(activityGameId, activityId, issueNumber)
            response = MsgPack()
            response.setResult("activityModel", activityModel.__dict__)
            response.setResult('allchip', chipCounter)
            return response.pack()
        except:
            ftlog.error()
            return self.makeErrorResponse().pack()

    def getActivityIssueMapConf(self, activityId):
        '''
        返回的第一个值err，若存在则代表发生错误
        返回的第二个值issueMap，若发生错误则为空
        '''
        actconf = TYActivityDaoImpl.getActivityConfig(activityId)
        ftlog.debug('BetguessHttpHandler.getActivityIssueMapConf:actconf=', actconf)
        if not actconf:
            return self.makeErrorResponse(-1, 'actconf not found! activityId maybe error').pack()

        issueMap = Tool.dictGet(actconf, 'config.issueMap', {})
        ftlog.debug('BetguessHttpHandler.getActivityIssueMapConf:issueMap=', issueMap)
        if not issueMap:
            return self.makeErrorResponse(-1, 'actconf.config.issueMap not found! actconf maybe error').pack()

        return None, issueMap

    @markHttpMethod(httppath='/gtest/dizhu/tableskin/conf')
    def doTableSkinConf(self, userId, clientId, version):
        clientId = clientId or sessiondata.getClientId(userId)
        msg = TableSkinTcpHandler._doTableSkinConf(userId, DIZHU_GAMEID, clientId, version)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/tableskin/mine')
    def doTableSkinMine(self, userId, clientId):
        clientId = clientId or sessiondata.getClientId(userId)
        msg = TableSkinTcpHandler._doTableSkinMine(userId, DIZHU_GAMEID, clientId)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/tableskin/setMine')
    def doTableSkinSetMine(self, userId, clientId, curSkinId, mySkinIds):
        clientId = clientId or sessiondata.getClientId(userId)
        model = MySkinModel(userId)
        if curSkinId:
            model.curSkin = curSkinId
        else:
            model.curSkin = None

        if mySkinIds:
            model.mySkins.update(mySkinIds)
        else:
            model.mySkins.clear()
        tableskin.saveMySkin(model)
        msg = TableSkinTcpHandler._doTableSkinMine(userId, DIZHU_GAMEID, clientId)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/tableskin/buy')
    def doTableSkinBuy(self, userId, clientId, version, skinId):
        clientId = clientId or sessiondata.getClientId(userId)
        msg = TableSkinTcpHandler._doTableSkinBuy(userId, DIZHU_GAMEID, clientId, version, skinId)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/tableskin/use')
    def doTableSkinUse(self, userId, clientId, version, skinId):
        clientId = clientId or sessiondata.getClientId(userId)
        msg = TableSkinTcpHandler._doTableSkinUse(userId, DIZHU_GAMEID, clientId, version, skinId)
        return msg

    @markHttpMethod(httppath='/gtest/dizhu/ft/pubfinishevent')
    def doPubFTFinishEvent(self, userId, gameId, roomId, tableId, ftId):
        event_remote.publishMyFTFinishEvent(gameId, userId, roomId, tableId, ftId)
        return {'result':'ok'}

    @markHttpMethod(httppath='/gtest/dizhu/arenamatch/quicksignin')
    def doArenmatchQuicksignin(self, userId, gameId, clientId, roomId, isTip):
        ftlog.info('doArenmatchQuicksignin start roomId=', roomId, 'gameId=', gameId)
        smsg = MsgPack()
        smsg.setCmd('room')
        smsg.setParam('action', 'quicksignin')
        smsg.setParam('userId', userId)
        smsg.setParam('gameId', gameId)
        smsg.setParam('clientId', clientId)
        smsg.setParam('roomId', roomId)
        smsg.setParam('isTip', isTip)
        smsg = smsg.pack()
        wrapper.send('GR6-001-998-1', smsg, '', '')
        return self.makeResponse('OK')

    @markHttpMethod(httppath='/gtest/dizhu/play/autoplay')
    def doArenmatchQuickstart(self, roomId, tableId, userId, clientId, gameId, seatId, isauto):
        ftlog.info('doDizhuPlayAutoPlay start userId=', userId, 'seatId=', seatId, 'isauto=', isauto)
        clientId = clientId or sessiondata.getClientId(userId)
        smsg = MsgPack()
        smsg.setCmd('table_call')
        smsg.setParam('action', 'auto_play')
        smsg.setParam('roomId', roomId)
        smsg.setParam('tableId', tableId)
        smsg.setParam('userId', userId)
        smsg.setParam('seatId', seatId)
        smsg.setParam('isauto', isauto)
        smsg.setParam('clientId', clientId)
        smsg.setParam('gameId', gameId)
        smsg = smsg.pack()
        wrapper.send('GT6-001-998-1', smsg, '', '')
        return self.makeResponse('OK')

    @markHttpMethod(httppath='/gtest/dizhu/dizhuled')
    def doSendLed(self, userName, roomName, reward):
        ledtext = [
            ['FFFFFF', '哇！'],
            ['FCF02D', str('张二蛋')],
            ['FFFFFF', ' 在斗地主 ' ],
            ['FCF02D', str('经典红包1亿元比赛')],
            ['FFFFFF', '中过五关斩六将夺得冠军，获得 '],
            ['FCF02D', '直升机一架']
        ]
        ledtext = dizhuled._mk_match_champion_rich_text(userName, roomName, reward)
        ftlog.info('hall led send:', ledtext)
        LedUtil.sendLed(ledtext, 'global')
        return self.makeResponse(ledtext)

    # 幸运礼包
    @markHttpMethod(httppath='/gtest/dizhu/todotask/kickout')
    def makeTodoTaskKickOut(self, gameId, userId, clientId, roomId):
        try:
            task = new_table_remote.processLoseRoundOver(gameId, userId, clientId, roomId)
        except Exception, e:
            task = {'errmsg': e.message}
        return task

    # 幸运礼包
    @markHttpMethod(httppath='/gtest/dizhu/todotask/luckbox')
    def makeTodoTaskLuckBox(self, gameId, userId, clientId):
        try:
            clientId = clientId or sessiondata.getClientId(userId)
            task = dizhupopwnd.generateDizhuLuckyBoxTodoTask(userId, clientId)
            if task:
                return self.makeResponse(task.toDict())
            return self.makeResponse({})
        except Exception, e:
            return self.makeErrorResponse(-1, e.message)

    # 离开房间
    @markHttpMethod(httppath='/gtest/dizhu/room/leave')
    def makeDizhuRoomLeave(self, roomId, userId, gameId, clientRoomId):
        ftlog.info('makeDizhuRoomLeave roomId=', roomId, 'gameId=', gameId, 'clientRoomId=', clientRoomId)
        smsg = MsgPack()
        smsg.setCmd('room_leave')
        smsg.setParam('clientRoomId', clientRoomId)
        smsg.setParam('userId', userId)
        smsg.setParam('roomId', roomId)
        smsg.setParam('clientId', sessiondata.getClientId(userId))
        smsg.setParam('gameId', gameId)
        smsg = smsg.pack()
        wrapper.send('GR6-001-998-1', smsg, '', '')
        return self.makeResponse('OK')


    ###############################################
    """
    千元积分赛，万元擂台赛 积分排行榜活动 测试接口
    """
    ###############################################
    @markHttpMethod(httppath='/gtest/dizhu/ranklist_bireport')
    def doRankListBiReportTest(self, userId, rankId):
        dizhu_score_ranking.scoreRankingBiReoprt(rankId, '20170807', userId, 15, 500)
        return self.makeResponse('doRankListBiReportTest OK')

    @markHttpMethod(httppath='/gtest/dizhu/ranklist_manager')
    def doGetScoreRankList(self, userId, rankId):
        smsg = MsgPack()
        smsg.setCmd('dizhu')
        smsg.setParam('action', 'scoreboard')
        smsg.setParam('userId', userId)
        smsg.setParam('gameId', 6)
        smsg.setParam('clientId', 'Android_3.97_weixinPay,tyGuest,tyAccount.yisdkpay.0-hall6.tuyoo.test')
        smsg.setParam('rankId', rankId)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doGetScoreRankList smsg=', smsg)
        return self.makeResponse('doGetScoreRankList OK')

    @markHttpMethod(httppath='/gtest/dizhu/getranklistbyissn')
    def doGetScoreRankingListByIssueNum(self, userId, rankId, issueNum, clientId):
        timestamp = pktimestamp.getCurrentTimestamp()
        msg = ScoreRankingHandler._doGetRankListByIssueNum(userId, rankId, issueNum, clientId, timestamp)
        ftlog.info('doGetScoreRankingListByIssueNum',
                   'userId=', userId,
                   'rankId=', rankId,
                   'issueNum=', issueNum,
                   'clientId=', clientId)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/score_get_reward')
    def doGetRanklistReward(self, userId, issn, rankId, isdibao):
        smsg = MsgPack()
        smsg.setCmd('dizhu')
        smsg.setParam('action', 'score_get_reward')
        smsg.setParam('gameId', 6)
        smsg.setParam('rankId', rankId)
        smsg.setParam('issn', issn)
        smsg.setParam('isDibao', isdibao)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doGetRanklistReward userId=', userId, 'smsg=', smsg)
        return self.makeResponse('doGetRanklistByIssn OK')

    @markHttpMethod(httppath='/gtest/dizhu/score_get_rule')
    def doGetRanklistRules(self, userId):
        smsg = MsgPack()
        smsg.setCmd('dizhu')
        smsg.setParam('action', 'score_get_rule')
        smsg.setParam('gameId', 6)
        smsg.setParam('rankId', 0)
        smsg.setParam('userId', userId)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doGetRanklistRules userId=', userId, 'smsg=', smsg)
        return self.makeResponse('doGetRanklistRules OK')

    @markHttpMethod(httppath='/gtest/dizhu/score_get_updateScore')
    def doGetRanklistUpdateScore(self, userId, chipDelta, winStreak, roomId, roundCount, issn):

        timeArray = time.strptime(issn, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))

        for i in range(roundCount):
            dizhu_score_ranking.updateUserScore(userId, roomId, chipDelta, winStreak, None, timeStamp)

        # userData = dizhu_score_ranking.loadUserData(userId, rankId, issueNum)
        ftlog.debug('doGetRanklistTestCmd updateScore userId=', userId,
                    'chipDelta=', chipDelta,
                    'winStreak=', winStreak,
                    'roomId=', roomId,
                    'roundCount=', roundCount)

        return self.makeResponse({'doGetRanklistUpdateScore userId=': userId,
                                  'chipDelta': chipDelta, 'winStreak': winStreak,
                                  'roomId': roomId, 'roundCount=': roundCount})

    @markHttpMethod(httppath='/gtest/dizhu/score_get_settle')
    def doGetRanklistSettle(self, userId, issn):

        timeArray = time.strptime(issn, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))

        dizhu_score_ranking.processRankings(timeStamp)

        ftlog.debug('doGetRanklistSettle settle userId=', userId,
                    'issn=', issn,
                    'timeStamp=', timeStamp)

        return self.makeResponse({'doGetRanklistSettle userId=': userId, 'issn': issn, 'timeStamp': timeStamp})

    @markHttpMethod(httppath='/gtest/dizhu/score_set_userdata')
    def doSetUserData(self, userId, rankId, issn, score=None, playCount=None, dibaoStu=None, rstu=None, rank=None, name=None, purl=None):
        timeArray = time.strptime(issn, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))
        issn = dizhu_score_ranking.calcIssueNum(timeStamp)

        userData = dizhu_score_ranking.loadOrCreateUserData(userId, rankId, issn)

        if score is not None:
            userData.score = score

        if playCount is not None:
            userData.playCount = playCount

        if dibaoStu is not None:
            userData.dibaoRewardState = dibaoStu

        if rstu is not None:
            userData.rewardState = rstu

        if rank is not None:
            userData.rank = rank

        if name is not None:
            userData.name = name

        if purl is not None:
            userData.purl = purl

        dizhu_score_ranking.saveUserData(userData)

        rankConf = dizhu_score_ranking.getConf().findRankingDefine(rankId)
        bigRoomId = rankConf.openRoomIds[0] if rankConf else None
        if bigRoomId:
            dizhu_score_ranking.updateUserScore(userId, bigRoomId, 0, 1, None, timeStamp)

        return self.buildScoreRankUserInfo(userData)

    @markHttpMethod(httppath='/gtest/dizhu/score_set_alluserdata')
    def doSetAllUserData(self, rankId, issn, score=None, playCount=None, dibaoStu=None, rstu=None, rank=None,
                      name=None, purl=None):

        timeArray = time.strptime(issn, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))
        issn = dizhu_score_ranking.calcIssueNum(timeStamp)

        userResponses = []
        for addUserId in range(10001, 10501):

            userData = dizhu_score_ranking.loadOrCreateUserData(addUserId, rankId, issn)
            if score is not None:
                userData.score = score
            if playCount is not None:
                userData.playCount = playCount
            if dibaoStu is not None:
                userData.dibaoRewardState = dibaoStu
            if rstu is not None:
                userData.rewardState = rstu
            if rank is not None:
                userData.rank = rank
            if name is not None:
                userData.name = name + str(addUserId)
            if purl is not None:
                userData.purl = purl

            dizhu_score_ranking.saveUserData(userData)
            dizhu_score_ranking.insertRanklist(rankId, userData.issueNum, userData.userId, userData.score, 500)

            userResponses.append(addUserId)
            ftlog.debug('score_set_alluserdata userInfo=', self.buildScoreRankUserInfo(userData))

            if (addUserId - 10000) % 50 == 0:
                time.sleep(0.5)

        return self.makeResponse({'userIds=':userResponses})

    @markHttpMethod(httppath='/gtest/dizhu/score_clear_ranklist')
    def doClearRankList(self, rankId, issn):
        userIdCleared = []

        # 清理玩家身上排行榜数据
        timeArray = time.strptime(issn, "%Y-%m-%d")
        timeStamp = int(time.mktime(timeArray))
        issueNum = dizhu_score_ranking.calcIssueNum(timeStamp)
        userIds = dizhu_score_ranking.getRanklist(rankId, issueNum, 0, -1)
        for rankUserId in userIds:
            dizhu_score_ranking.removeUserData(rankUserId, rankId, issueNum)
            userIdCleared.append(rankUserId)
            ftlog.debug('doClearRankList userId=', rankUserId, 'rankId=', rankId, 'issueNum=', issueNum)

        # 清理历史期号数据
        dizhu_score_ranking.clearRankingIssueNum(rankId, issueNum)
        rankingInfo = dizhu_score_ranking.loadRankingInfo(rankId)
        ret = ''
        for index in range(rankingInfo.itemCount):
            if rankingInfo.items[index] == issueNum:
                rankingInfo.items.pop(index)
                dizhu_score_ranking.saveRankingInfo(rankingInfo)
                ret = str(rankingInfo.items[index]) + ' cleared success '

        # 清理名人堂数据
        fameHall = dizhu_score_ranking.loadFameHall(rankId)
        removedItems = fameHall.trim(0)
        dizhu_score_ranking.saveFameHall(fameHall)
        ftlog.info('dizhu_score_ranking.setFameHall', 'rankId=', rankId, 'issueNum=', issueNum,
                   'removedIssues=', [item.issueNum for item in removedItems])

        return self.makeResponse({'doClearRankList rankId': rankId,
                                  'issueNum': issueNum,
                                  'This userId Cleared=': userIdCleared,
                                  'famehall cleared=': [item.issueNum for item in removedItems],
                                  'and history cleared. ret=': ret})

    @markHttpMethod(httppath='/gtest/dizhu/score_execute_cmd')
    def doExecuteCmd(self, rankId, issn):
        if len(issn) != 8:
            return self.makeResponse({'score_execute_cmd rankId': rankId, 'issueNum=': issn})
        issueNum = str(issn)
        for rankId in ['0', '1']:
            rank = 0
            userInfos = dizhu_score_ranking.getRanklist(rankId, issueNum, 0, -1)
            if not userInfos:
                return self.makeResponse({'score_execute_cmd issn not found rankId': rankId, 'issueNum=': issn})
            for userId in userInfos:
                rank += 1
                userData = dizhu_score_ranking.loadUserData(userId, rankId, issueNum)
                userData.rank = rank
                dizhu_score_ranking.saveUserData(userData)
                ftlog.info('score_execute_cmd userId=', userId, 'rankId=', rankId, 'issueNum=', issueNum, 'rank=',
                           rank)

        ftlog.info('hotfix_score_ranking_rank over issueNum=', issueNum)
        return self.makeResponse({'score_execute_cmd rankId': rankId, 'issueNum=': issn, 'execute over ret=': 0})

    @markHttpMethod(httppath='/gtest/dizhu/score_reward_tip')
    def doGetNotReceiveReward(self, userId):
        smsg = MsgPack()
        smsg.setCmd('dizhu')
        smsg.setParam('action', 'score_reward_tip')
        smsg.setParam('gameId', 6)
        smsg.setParam('userId', userId)
        smsg.setParam('clientId', "Android_3.97_tyOneKey,tyAccount,tyGuest.yisdkpay.0-hall6.ddzTest.dj")

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.debug('doGetNotReceiveReward userId=', userId, 'smsg=', smsg)
        return self.makeResponse({'doGetNotReceiveReward OK smsg=': smsg})

    @markHttpMethod(httppath='/gtest/dizhu/init_user_data')
    def doExecuteCmd(self, userId, rankId, issueNum):
        ret = 0
        if len(issueNum) != 8:
            return self.makeResponse({'score_execute_cmd issueNum Error. rankId': rankId, 'issueNum=': issueNum})
        issueNum = str(issueNum)
        userData = dizhu_score_ranking.loadUserData(userId, rankId, issueNum)
        if userData:
            userData = dizhu_score_ranking.UserData(userId, rankId, issueNum)
            ret = dizhu_score_ranking.saveUserData(userData)
            rankingDefine = dizhu_score_ranking.getConf().findRankingDefine(rankId)
            rankLimit = rankingDefine.rankLimit if rankingDefine else 3000
            dizhu_score_ranking.insertRanklist(rankId, issueNum, issueNum, 0, rankLimit)
            ftlog.info('del scoreRanking userData success. userId=', userId, 'rankId=', rankId, 'issueNum=', issueNum)

        return self.makeResponse({'score_execute_cmd del scoreRanking userData. rankId': rankId, 'issueNum=': issueNum, 'execute over ret=': ret})
    ###############################################
    """
    华为大师杯  积分排行榜活动
    """
    @classmethod
    def _check_param_activityId(cls, key, params):
        activityId = runhttp.getParamStr(key)
        if not isstring(activityId):
            return 'param activityId error', None
        return None, activityId

    @classmethod
    def _check_param_activityType(cls, key, params):
        activityType = runhttp.getParamStr(key)
        if not isstring(activityType):
            return 'param activityId error', None
        return None, activityType

    @classmethod
    def _check_param_totalIssueNum(cls, key, params):
        totalIssueNum = runhttp.getParamStr(key)
        if not isstring(totalIssueNum):
            return 'param totalIssueNum error', None
        return None, totalIssueNum

    @classmethod
    def _check_param_delDate(cls, key, params):
        delDate = runhttp.getParamStr(key)
        if not isstring(delDate):
            return 'param delDate error', None
        return None, delDate

    @markHttpMethod(httppath='/gtest/dizhu/activity_score')
    def doRankListActivityInfo(self, userId, activityId, activityType):
        smsg = MsgPack()
        smsg.setCmd('act')
        smsg.setParam('action', 'scoreboardActivity')
        smsg.setParam('userId', userId)
        smsg.setParam('clientId', "Android_3.97_360.360,yisdkpay.0-hall6.360.win")
        smsg.setParam('activityId', activityId)
        smsg.setParam('gameId', 6)
        smsg.setParam('type', activityType)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doRankListActivityInfo userId=', userId, 'smsg=', smsg)
        return self.makeResponse(smsg)

    @markHttpMethod(httppath='/gtest/dizhu/activity_reward')
    def doRankListActivityUserRewardInfo(self, userId, activityId):
        smsg = MsgPack()
        smsg.setCmd('act')
        smsg.setParam('action', 'scoreboardActivity_rewardInfo')
        smsg.setParam('userId', userId)
        smsg.setParam('activityId', activityId)
        smsg.setParam('gameId', 6)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doRankListActivityUserRewardInfo userId=', userId, 'smsg=', smsg)
        return self.makeResponse(smsg)

    @markHttpMethod(httppath='/gtest/dizhu/activity_gain_reward')
    def doRankListActivityGainReward(self, userId, activityId):
        smsg = MsgPack()
        smsg.setCmd('act')
        smsg.setParam('action', 'scoreboardActivity_gainReward')
        smsg.setParam('userId', userId)
        smsg.setParam('gameId', 6)
        smsg.setParam('activityId', activityId)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doRankListActivityUserRewardInfo userId=', userId, 'smsg=', smsg)
        return self.makeResponse(smsg)

    @markHttpMethod(httppath='/gtest/dizhu/activity_userData')
    def doRankListActivityUserData(self, userId, rankId, issueNum, score=None, rank=None, name=None, rstu=None):
        # 大师杯 修改玩家数据接口
        from dizhu.activitynew import activity_score_ranking
        userData = activity_score_ranking.loadOrCreateUserData(userId, rankId, issueNum)

        if score is not None:
            userData.score = score

        if rank is not None:
            userData.rank = rank

        if name is not None:
            userData.name = name

        if rstu is not None:
            userData.rewardStu = rstu
            userData.dibaoStu = rstu

        activity_score_ranking.saveUserData(userData)
        activity_score_ranking.insertRankList(rankId, issueNum, userId, userData.score, 500)
        return self.makeResponse(userData.toDict())

    @markHttpMethod(httppath='/gtest/dizhu/activity_add_userData')
    def doSetActivityAllUserData(self, rankId, issueNum, begin, end, score=None, rank=None, name=None, rstu=None):
        # 大师杯活动 增加假数据接口
        from dizhu.activitynew import activity_score_ranking
        userResponses = []
        for addUserId in range(begin, end):
            userData = activity_score_ranking.loadOrCreateUserData(addUserId, str(rankId), issueNum)
            if score is not None:
                userData.score = score + int(addUserId)
            if rstu is not None:
                userData.rewardStu = rstu
            if rank is not None:
                userData.rank = rank
            if name is not None:
                userData.name = name + str(addUserId)

            activity_score_ranking.saveUserData(userData)
            activity_score_ranking.insertRankList(rankId, issueNum, addUserId, userData.score, 500)
            userResponses.append(addUserId)
            ftlog.debug('doSetActivityAllUserData userData=', userData.toDict())

            if (addUserId - 10000) % 50 == 0:
                time.sleep(0.5)

        return self.makeResponse({'userIds=': userResponses})

    @markHttpMethod(httppath='/gtest/dizhu/activity_remove_alluserdata')
    def doActivityRemoveRankList(self, rankId, issueNum):
        # 大师杯 移除对应活动actId对应issueNum数据的接口
        from dizhu.activitynew import activity_score_ranking
        userIdList = activity_score_ranking.getRankList(rankId, issueNum, 0, -1)
        for userId in userIdList:
            userData = activity_score_ranking.loadUserData(userId, rankId, issueNum)
            if userData:
                initUserData = activity_score_ranking.UserData(userId, rankId, issueNum)
                activity_score_ranking.saveUserData(initUserData)
                if ftlog.is_debug():
                    ftlog.debug('activity_remove_alluserdata userData=', userData.toDict())

        activity_score_ranking.removeRanklist(rankId, issueNum)

        rankingInfo = activity_score_ranking.ActivityScoreRankingInfo(rankId)
        activity_score_ranking.saveActivityScoreRankingInfo(rankingInfo)

        return self.makeResponse({'remove rankList rankId=': rankId, 'issueNum=': issueNum})


    @markHttpMethod(httppath='/gtest/dizhu/activity_processing')
    def doRankListActivityProcessing(self, rankId, issueNum, totalIssueNum, delDate):
        # 大师杯活动结算对应actId下对应issueNum期接口
        import dizhu.activitynew.activity_score_ranking as activity
        activity.processRanking(rankId, totalIssueNum, delDate, issueNum)
        return self.makeResponse({'activity_processing ok rankId=': rankId,
                                  'issueNum=': issueNum,
                                  'delDate=':delDate,
                                  'totalIssueNum=':totalIssueNum})

    @markHttpMethod(httppath='/gtest/dizhu/activity_remove_rankingInfo')
    def doRemoveRankingInfo(self, rankId, issueNum):
        from dizhu.activitynew import activity_score_ranking
        rankingInfo = activity_score_ranking.loadActivityScoreRankingInfo(rankId)
        while rankingInfo.itemCount > 0:
            rankingInfo.items.pop(0)

        activity_score_ranking.saveActivityScoreRankingInfo(rankingInfo)
        return self.makeResponse({'activity_remove_rankingInfo ok': rankingInfo.toDict()})

    ###############################################
    @classmethod
    def _check_param_recordId(cls, key, params):
        recordId = runhttp.getParamInt(key)
        if not isinstance(recordId, int):
            return 'param recordId error', None
        return None, recordId

    @classmethod
    def _check_param_matchId(cls, key, params):
        matchId = runhttp.getParamInt(key)
        if not isinstance(matchId, int):
            return 'param matchId error', None
        return None, matchId

    @classmethod
    def _check_param_ledText(cls, key, params):
        ledText = runhttp.getParamStr(key)
        if not isstring(ledText):
            return 'param ledText error', None
        return None, ledText

    @markHttpMethod(httppath='/gtest/dizhu/match_lottery')
    def doTestMatchLottery(self, userId, matchId, rank, recordId):
        # 比赛翻拍抽奖 测试接口
        from dizhu.games.matchutil import MatchLottery
        match_lottery = MatchLottery(-1, 1)
        lotteryReward, items = match_lottery.chooseReward(userId, matchId, rank, recordId)
        return self.makeResponse({'match_lottery userId=': userId, 'lotteryReward=': lotteryReward, 'items=': items})

    @markHttpMethod(httppath='/gtest/dizhu/activity_processing_remove')
    def doTestActivityProcessing(self, rankId):
        from dizhu.activitynew.activity_score_ranking import removeRankUserData
        removeRankUserData(rankId)
        return self.makeResponse({'activity_processing_remove ok rankId=': rankId})

    @markHttpMethod(httppath='/gtest/dizhu/match_lottery_test')
    def doTestMatchLottery(self, userId):
        from hall.servers.util.rpc import event_remote
        event_remote.publishMatchWinloseEvent(6, userId, 6072, True, 1, 10)
        return self.makeResponse({'match_lottery_test ok param': 'match_lottery_test'})

    @markHttpMethod(httppath='/gtest/dizhu/add_led_text')
    def doAddFakeTestLedText(self, userId, ledText):
        LedUtil.saveLedText(ledText)
        return self.makeResponse({'add_led_text ok. ledText=': ledText})

    @markHttpMethod(httppath='/gtest/dizhu/get_led_text')
    def doTestLedText(self, userId):
        smsg = MsgPack()
        smsg.setCmd('dizhu')
        smsg.setParam('action', 'get_led_text')
        smsg.setParam('userId', userId)
        smsg.setParam('clientId', "Android_3.97_360.360,yisdkpay.0-hall6.360.win")
        smsg.setParam('gameId', 6)

        smsg = smsg.pack()
        router.sendUtilServer(smsg, userId)

        ftlog.info('doTestLedText userId=', userId, 'smsg=', smsg)

        return self.makeResponse({'get_led_text ok. msg=': smsg})

    ###############################################

    @markHttpMethod(httppath='/gtest/dizhu/ntask/setTasks')
    def doNTaskSetTasks(self, userId, taskIdList):
        try:
            ftlog.info('doNTaskSetTasks userId=', userId,
                       'taskIdList=', taskIdList)
            newTaskIdList = task_remote.setNewbieTasks(6, userId, taskIdList, True)
            return self.makeResponse({'taskIdList': newTaskIdList})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ntask/setProgress')
    def doNTaskSetProgress(self, userId, taskId, progress):
        try:
            ftlog.info('doNTaskSetProgress userId=', userId,
                       'taskId=', taskId,
                       'progress=', progress)
            changed, finishCount, newProgress = task_remote.setNewbieTaskProgress(6, userId, taskId, progress)
            return self.makeResponse({'changed': changed, 'finishCount': finishCount, 'progress': newProgress})
        except Exception, e:
            ftlog.error()
            return self.makeErrorResponse(str(e), 'RPC错误')

    @markHttpMethod(httppath='/gtest/dizhu/ntask/getTaskProgress')
    def doGetTaskProgress(self, userId):
        info = task_remote.getTaskProgress(6, userId)
        return self.makeResponse(info)

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_gain_reward')
    def doScoreRankGainReward(self, userId, rankId, issueNum, isdibao, clientId):
        from dizhu.servers.util.score_ranklist_handler import ScoreRankingHandler
        msg = ScoreRankingHandler._doGetRankReward(userId, rankId, issueNum, isdibao, clientId)
        ftlog.info('doScoreRankGainReward',
                   'userId=', userId,
                   'rankId=', rankId,
                   'issueNum=', issueNum,
                   'isdibao=', isdibao,
                   'clientId=', clientId)
        return self.makeResponse(msg._ht)

    def buildScoreRankUserInfo(self, userData):
        return self.makeResponse({'userData':{
                                        'rankId':userData.rankId,
                                        'score':userData.score,
                                        'playCount':userData.playCount,
                                        'dibaoRewardState':userData.dibaoRewardState,
                                        'rewardState':userData.rewardState,
                                        'rank':userData.rank,
                                        'name':userData.name,
                                        'purl':userData.purl
                                    },
                                    'rankInList':dizhu_score_ranking.getUserRank(userData.userId, userData.rankId, userData.issueNum)
                                })

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_get_user_info')
    def doScoreRankGetUserInfo(self, userId, rankId, issueNum, clientId):
        userData = dizhu_score_ranking.loadUserData(userId, rankId, issueNum)
        return self.buildScoreRankUserInfo(userData)

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_update_score')
    def doScoreRankUpdateScore(self, userId, chipDelta, winStreak, roomId, roundCount, issueNum, clientId):
        timestamp = pktimestamp.timestrToTimestamp(issueNum, '%Y%m%d')

        for _ in range(roundCount):
            dizhu_score_ranking.updateUserScore(userId, roomId, chipDelta, winStreak, None, timestamp)

        ftlog.info('doScoreRankUpdateScore',
                   'userId=', userId,
                   'chipDelta=', chipDelta,
                   'winStreak=', winStreak,
                   'roomId=', roomId,
                   'roundCount=', roundCount,
                   'issueNum=', issueNum,
                   'clientId=', clientId)

        rankingDefine = dizhu_score_ranking.getConf().rankDefineForRoomId(roomId)
        if rankingDefine:
            userData = dizhu_score_ranking.loadUserData(userId, rankingDefine.rankId, issueNum)
            return self.buildScoreRankUserInfo(userData)
        return self.makeErrorResponse(-1, '该房间没有对应的排行榜')

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_get_list_by_issue')
    def doScoreRankGetListByIssue(self, userId, rankId, issueNum, clientId, begin=None, end=None):
        timestamp = pktimestamp.getCurrentTimestamp()
        from dizhu.servers.util.score_ranklist_handler import ScoreRankingHandler
        msg = ScoreRankingHandler._doGetRankListByIssueNum(userId, rankId, issueNum, clientId, begin, end, timestamp)
        ftlog.info('doScoreRankGetListByIssue',
                   'userId=', userId,
                   'rankId=', rankId,
                   'issueNum=', issueNum,
                   'clientId=', clientId)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_get_rules')
    def doScoreRankGetRules(self, userId, rankId):
        msg = ScoreRankingHandler._doGetRankRules(userId, rankId)
        ftlog.info('doScoreRankGetListByIssue',
                   'userId=', userId,
                   'rankId=', rankId)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_scoreboard')
    def doScoreRankScoreboard(self, userId, rankId, clientId, nowTime):
        msg = ScoreRankingHandler._doGetRankList(userId, rankId, clientId, nowTime)
        ftlog.info('doScoreRankScoreboard',
                   'userId=', userId,
                   'rankId=', rankId,
                   'clientId=', clientId)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/score_rank_process')
    def doScoreRankProcess(self, rankId, nowTime):
        dizhu_score_ranking.processRankings(nowTime)
        rankingInfo = dizhu_score_ranking.loadRankingInfo(rankId)
        d = rankingInfo.toDict()
        return self.makeResponse({'rankId':rankId, 'info':d})

    @markHttpMethod(httppath='/gtest/dizhu/fishing_fish')
    def doFishingFish(self, userId, baitId):
        return self.makeResponse({'info': FishHelper.getFishReward(userId, baitId)})

    @markHttpMethod(httppath='/gtest/dizhu/fishing_info')
    def doFishingInfo(self, userId):
        return self.makeResponse({'info': FishHelper.getFishingInfo(userId)})

    @markHttpMethod(httppath='/gtest/dizhu/fishing_history')
    def doFishingHistory(self, userId):
        return self.makeResponse({'info': FishHelper.getFishingHistory()})

    @markHttpMethod(httppath='/gtest/dizhu/zhaociji')
    def doZhaociji(self, userId):
        from dizhu.servers.util.game_handler import GameTcpHandler
        return self.makeResponse({'info': GameTcpHandler.getZhaocijiGames(userId, DIZHU_GAMEID, sessiondata.getClientId(userId))})


    # *******************************
    #           天梯赛相关接口
    # *******************************

    @markHttpMethod(httppath='/gtest/dizhu/segment_match_rules')
    def doSegmentMatchGetRules(self, userId, gameId, clientId):
        from dizhu.servers.util.segment_match_handler import SegmentMatchHandler
        msg = SegmentMatchHandler._get_segment_rules(userId, gameId, clientId)
        ftlog.info('doSegmentMatchGetRules',
                   'userId=', userId,
                   'gameId=', gameId,
                   'clientId=', clientId,
                   'msg=', msg._ht)
        return self.makeResponse(msg._ht)


    @markHttpMethod(httppath='/gtest/dizhu/segment_info')
    def doSegmentMatchUserInfo(self, userId, gameId, clientId, issue):
        from dizhu.servers.util.segment_match_handler import SegmentMatchHandler
        msg = SegmentMatchHandler._get_segment_info(userId, gameId, clientId, issue)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/segment_rankList')
    def doSegmentMatchRankList(self, userId, gameId, clientId, start, stop, preIssue):
        from dizhu.servers.util.segment_match_handler import SegmentMatchHandler
        msg = SegmentMatchHandler._get_segment_rank_list(userId, gameId, clientId, start, stop, preIssue)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/segment_settle')
    def doSegmentMatchSettle(self, state):
        # 结算赛季
        from dizhu.entity.segment.dizhu_segment_match import _processIssueStateList
        _processIssueStateList(forceSettle=state)
        return self.makeResponse('ok')

    # 结算赛季，给用户发奖
    @markHttpMethod(httppath='/gtest/dizhu/segment_reward')
    def doSegmentMatchReward(self, userId):
        from dizhu.entity.segment.dizhu_segment_rewards import DizhuSegmentRewardsHelper
        evt = EventUserLogin(userId, 6, True, True, 'xxxxxxxxxx')
        DizhuSegmentRewardsHelper.processEnterGame(evt)
        return self.makeResponse('ok')


    @markHttpMethod(httppath='/gtest/dizhu/segment_issueList')
    def doSegmentMatchIssueList(self, userId, gameId, clientId):
        from dizhu.servers.util.segment_match_handler import SegmentMatchHandler
        msg = SegmentMatchHandler._get_segment_issues(userId, gameId, clientId)
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/segment_info_update')
    def doSegmentMatchUpdate(self, userId, issue, segment, stars, state, inherit):
        from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper, _addUserToRewardPool, UserSegmentDataIssue
        userData = SegmentMatchHelper.getUserSegmentDataIssue(userId, issue) or UserSegmentDataIssue()
        userData.segment = segment
        userData.currentStar = stars
        userData.poolRewardsState = state
        userData.segmentRewardsState = state
        userData.inherit = inherit
        # 插入排行榜
        from dizhu.entity.segment.dizhu_segment_match import insertRanklist
        insertRanklist(issue, userId, userData.segment * 100 + userData.currentStar)
        # 获取排名
        rank = SegmentMatchHelper.getUserRealRank(userId, issue)
        userData.rank = rank

        seasonInfo = SegmentMatchHelper.getSeasonInfo(issue)
        if seasonInfo.poolRewards.get('type') == 'segment':
            _addUserToRewardPool(seasonInfo, userId)

        # 保存用户信息
        SegmentMatchHelper.saveUserSegmentDataIssue(userId, issue, userData)
        return self.makeResponse(userData.toDict())


    @markHttpMethod(httppath='/gtest/dizhu/segment/cur_task/progress/set')
    def doSetCurTaskProgress(self, userId):
        progress = runhttp.getParamInt("progress")
        if not progress >= 0:
            return self.makeErrorResponse(message='progress err')
        ret, info = task_remote.setSegmentTaskProgress(6, userId, progress)
        return self.makeResponse({'result': ret, 'msg': info})

    @markHttpMethod(httppath='/gtest/dizhu/segment/task/remove')
    def doSegmentTaskRemove(self, userId):
        reset_type = runhttp.getParamStr("t")
        from dizhu.entity.segment import task
        if reset_type == 'daily':
            key = task.daily_key(userId)
            daobase.executeUserCmd(userId, "DEL", key)
        elif reset_type == 'newbie':
            key = task.newbie_key(userId)
            daobase.executeUserCmd(userId, "DEL", key)
        else:
            return self.makeErrorResponse(message='type err')
        return self.makeResponse({'result': 0, 'msg': 'success'})

    @markHttpMethod(httppath='/gtest/dizhu/segment/task/reset_time/set')
    def doSegmentTaskTimeSet(self):
        timestamp = runhttp.getParamInt("ts")
        if timestamp < 30:
            return self.makeErrorResponse(message='timestamp cannot < 30')
        for i in range(router._utilServer.sidlen):
            ret, info = task_remote.doSegmentTaskTimeSet(6, timestamp)
        return self.makeResponse({'result': True, 'msg': 'success'})

    @markHttpMethod(httppath='/gtest/dizhu/watch/ad')
    def doWatchAd(self, userId, adId):
        from dizhu.servers.util.segment_match_handler import SegmentMatchHandler
        msg = SegmentMatchHandler._do_watch_ad(userId, 6, adId, 'aaaaaa')
        return self.makeResponse(msg._ht)

    @markHttpMethod(httppath='/gtest/dizhu/daily/checkin')
    def doDailyCheckIn(self, userId):
        clientId = sessiondata.getClientId(userId)
        ftlog.debug('ddz.test.doDailyCheckIn',
                    'userId=', userId,
                    'gameId=', 6,
                    'clientId=', clientId)
        msg = MsgPack()
        conf = configure.getGameJson(6, 'daily.checkin', {})
        conditon = conf.get('condition')
        from hall.entity.hallusercond import UserConditionRegister
        cond = UserConditionRegister.decodeFromDict(conditon)
        timestamp = pktimestamp.getCurrentTimestamp()
        retCheck = cond.check(DIZHU_GAMEID, userId, clientId, timestamp)
        msg.setCmd('dizhu')
        msg.setResult('action', 'checkin_daily')
        if not retCheck:
            msg.setResult('show', 0)
            return msg.pack()
        signInRewards = conf.get('signInRewards')
        newSignInRewards = []
        for dayRewards in signInRewards:
            day = dayRewards.get('day')
            isGet = 1 if daobase.executeUserCmd(userId, 'HGET', 'checkInReward:' + str(6) + ':' + str(userId), day) else 0
            dayRewards.update({'isGet': isGet})
            newSignInRewards.append(dayRewards)
        registerDays = UserInfo.getRegisterDays(userId, timestamp)
        msg.setResult('show', 1)
        msg.setResult('registerDays', registerDays)
        msg.setResult('signInRewards', newSignInRewards)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/sendReward/checkin')
    def doSendReward(self, userId, dayNumber):
        ftlog.debug('ddz.test.doSendReward',
                    'userId=', userId,
                    'gameId=', 6,
                    'dayNumber=', dayNumber)
        conf = configure.getGameJson(6, 'daily.checkin', {})
        signInRewards = conf.get('signInRewards')
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'send_rewards')
        isGet = 1 if daobase.executeUserCmd(userId, 'HGET', 'checkInReward:' + str(6) + ':' + str(userId), dayNumber) else 0
        if isGet:
            msg.setResult('isGet', 0)
            return msg.pack()
        for dayRewards in signInRewards:
            if dayRewards.get('day') == dayNumber:
                rewardsList = dayRewards.get('rewards')
                contentItems = TYContentItem.decodeList(rewardsList)
                assetList = dizhu_util.sendRewardItems(userId, contentItems, '', 'DIZHU_QIANDAO_SEND_REWARD', 0)
                daobase.executeUserCmd(userId, 'HSET', 'checkInReward:' + str(6) + ':' + str(userId), dayNumber, 1)
                msg.setResult('isGet', 1)
                return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/doRoundInfo')
    def doRoundInfo(self, userId):
        ftlog.debug('ddz.test.doRoundInfo',
                    'userId=', userId,
                    'gameId=', 6)
        roundInfo = dizhu_new_roundlist.getUserNewRoundInfo(userId)
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'roundlist')
        msg.setResult('gameId', 6)
        msg.setResult('userId', userId)
        msg.setResult('roundInfo', roundInfo)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/deltaUserAsset')
    def doDeltaUserAsset(self, userId, itemId, assetCount):
        FTTimer(0, functools.partial(deltaUserAsset, userId, itemId, assetCount))

    @markHttpMethod(httppath='/gtest/dizhu/updateSegment')
    def doUpdateSegment(self, userId, issueNum, segment, stars):
        FTTimer(0, functools.partial(updateSegment, userId, issueNum, segment, stars))

    @markHttpMethod(httppath='/gtest/dizhu/active/list')
    def doActiveInfoList(self, userId):
        infoList = ActivityWxUserActive()._activeInfoList(userId)
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'active_list')
        msg.setResult('gameId', 6)
        msg.setResult('userId', userId)
        msg.setResult('infoList', infoList)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/active/sendRewards')
    def doActiveSendReward(self, userId, rewardKind, scheduleId):
        sendReward = ActivityWxUserActive()._sendActiveReward(userId, rewardKind, scheduleId)
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'active_reward')
        msg.setResult('gameId', 6)
        msg.setResult('userId', userId)
        msg.setResult('infoList', sendReward)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/signIn/list')
    def signInList(self, userId):
        signInList = dizhu_signin._signInList(userId)
        state = signInList.get('state', 0)
        signInDay = signInList.get('signInDay', 0)
        rewardList = signInList.get('rewardList', {})
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'signInList')
        msg.setResult('gameId', 6)
        msg.setResult('userId', userId)
        msg.setResult('state', state)
        msg.setResult('signInDay', signInDay)
        msg.setResult('rewardList', rewardList)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/dizhu/signIn/rewards')
    def signInRewards(self, userId, day, typeId):
        state = dizhu_signin._sendRewards(userId, day, typeId)
        msg = MsgPack()
        msg.setCmd('dizhu')
        msg.setResult('action', 'signInRewards')
        msg.setResult('gameId', 6)
        msg.setResult('userId', userId)
        msg.setResult('state', state)
        router.sendToUser(msg, userId)
        return msg.pack()

    @markHttpMethod(httppath='/gtest/hall/share/control')
    def testShareControl(self, gameId, userId, pointId, whereToShare):
        from hall.servers.util.share3_handler import Share3TcpHandler
        clientId = sessiondata.getClientId(userId)
        mp = Share3TcpHandler._doGetShareReward(gameId, userId, clientId, pointId, whereToShare)
        if mp:
            router.sendToUser(mp, userId)
            return mp.pack()


def deltaUserAsset(userId, itemId, count):
    from poker.entity.biz.content import TYContentItem
    from dizhu.entity import dizhu_util
    from hall.servers.util.rpc import user_remote

    if count == 0:
        return

    if count > 0:
        # 增加
        contentItems = TYContentItem.decodeList([{'itemId': itemId, 'count': count}])
        dizhu_util.sendRewardItems(userId, contentItems, '', 'DIZHU_GDSS_SIGNED_REWARD', 0)

    else:
        # 消费
        contentItemList = [{'itemId': itemId, 'count': abs(count)}]
        user_remote.consumeAssets(6, userId, contentItemList, 'DIZHU_GDSS_SIGNED_REWARD', 0)


def updateSegment(userId, issueNum, segment, star):
    from dizhu.entity.segment.dizhu_segment_match import SegmentMatchHelper, UserSegmentDataIssue
    userData = SegmentMatchHelper.getUserSegmentDataIssue(userId, issueNum) or UserSegmentDataIssue()
    userData.segment = segment
    userData.currentStar = star
    # 保存用户信息
    SegmentMatchHelper.saveUserSegmentDataIssue(userId, issueNum, userData)
