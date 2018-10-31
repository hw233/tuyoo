# -*- coding: utf-8 -*-
"""
Created on 2016年7月14日

@author: zhaojiangang
"""
import random
from freetime.core import reactor
import freetime.util.log as ftlog
from poker.entity.game.rooms import roominfo
from poker.entity.game.rooms.erdayi_match_ctrl.config import MatchConfig
from poker.entity.game.rooms.erdayi_match_ctrl.const import MatchFinishReason
from poker.entity.game.rooms.erdayi_match_ctrl.interface import MatchStage, MatchFactory
from poker.entity.game.rooms.erdayi_match_ctrl.interfacetest import MatchStatusDaoMem, SigninRecordDaoTest, TableControllerTest, PlayerNotifierTest, MatchRewardsTest, MatchUserIFTest, SignerInfoLoaderTest
from poker.entity.game.rooms.erdayi_match_ctrl.match import MatchMaster, MatchAreaLocal, MatchInst
from poker.entity.game.rooms.erdayi_match_ctrl.models import Player, TableManager
from poker.entity.game.rooms.erdayi_match_ctrl.utils import Logger, HeartbeatAble
match_conf = {'buyinchip': 0, 'controlServerCount': 1, 'controlTableCount': 0, 'dummyUserCount': 0, 'gameServerCount': 20, 'gameTableCount': 500, 'goodCard': 0, 'hasrobot': 0, 'ismatch': 1, 'matchConf': {'desc': '\xe5\xbc\x80\xe8\xb5\x9b\xe6\x97\xb6\xe9\x97\xb4\xef\xbc\x9a21:30 \n\xe6\x8a\xa5\xe5\x90\x8d\xe8\xb4\xb9\xe7\x94\xa8\xef\xbc\x9a\xe5\x85\x8d\xe8\xb4\xb9', 'fees': [], 'rank.rewards': [{'desc': '\xe4\xbb\xb7\xe5\x80\xbc1499\xe5\x85\x83\xe7\x9a\x84\xe6\xb8\xb8\xe6\x88\x8f\xe8\x80\xb3\xe6\x9c\xba', 'ranking': {'end': 1, 'start': 1}, 'rewards': [{'count': 1, 'itemId': 'item:4151'}]}, {'desc': '10\xe4\xb8\x87\xe9\x87\x91\xe5\xb8\x81', 'ranking': {'end': 4, 'start': 2}, 'rewards': [{'count': 100000, 'itemId': 'user:chip'}]}, {'desc': '1\xe4\xb8\x87\xe9\x87\x91\xe5\xb8\x81', 'ranking': {'end': 10, 'start': 5}, 'rewards': [{'count': 10000, 'itemId': 'user:chip'}]}], 'stages': [{'animation.type': 0, 'card.count': 6, 'chip.base': 1000, 'chip.grow': 0.3, 'chip.grow.base': 200, 'chip.grow.incr': 100, 'chip.times': 60, 'chip.user': 12000, 'chip.user.2.rate': 0, 'chip.user.3.base': 0, 'lose.user.chip': 0.5, 'name': '\xe6\xb5\xb7\xe9\x80\x89\xe8\xb5\x9b', 'rise.user.count': 24, 'rise.user.refer': 30, 'seat.principles': 1, 'grouping.type': 2, 'grouping.user.count': 30, 'type': 1}, {'animation.type': 1, 'card.count': 2, 'chip.base': 100, 'chip.grow': 0.5, 'chip.times': 3600, 'chip.user': 3, 'chip.user.3.base': 300, 'name': '24\xe5\xbc\xba\xe8\xb5\x9b', 'rise.user.count': 12, 'seat.principles': 2, 'type': 2}, {'animation.type': 1, 'card.count': 2, 'chip.base': 100, 'chip.grow': 0.5, 'chip.times': 3600, 'chip.user': 2, 'chip.user.2.rate': 0.2, 'name': '12\xe5\xbc\xba\xe8\xb5\x9b', 'rise.user.count': 6, 'seat.principles': 2, 'type': 2}, {'animation.type': 3, 'card.count': 2, 'chip.base': 100, 'chip.grow': 0.5, 'chip.times': 3600, 'chip.user': 2, 'chip.user.2.rate': 0.2, 'name': '6\xe5\xbc\xba\xe8\xb5\x9b', 'rise.user.count': 3, 'seat.principles': 2, 'type': 2}, {'animation.type': 2, 'card.count': 2, 'chip.base': 100, 'chip.grow': 0.5, 'chip.times': 3600, 'chip.user': 2, 'chip.user.2.rate': 0.2, 'name': '\xe5\x86\xb3\xe8\xb5\x9b', 'rise.user.count': 1, 'seat.principles': 2, 'type': 2}], 'start': {'fee.type': 0, 'maxplaytime': 7200, 'prepare.times': 0, 'signin.times': 2400, 'start.speed': 6, 'times': {'days': {'first': '', 'interval': '1d', 'count': 100}, 'times_in_day': {'first': '00:00', 'interval': 1, 'count': 2000}}, 'type': 2, 'user.groupsize': 2000, 'user.maxsize': 2000, 'user.minsize': 3, 'user.next.group': 0}, 'table.seat.count': 3, 'tips': {'infos': ['\xe7\xa7\xaf\xe5\x88\x86\xe7\x9b\xb8\xe5\x90\x8c\xe6\x97\xb6\xef\xbc\x8c\xe6\x8c\x89\xe6\x8a\xa5\xe5\x90\x8d\xe5\x85\x88\xe5\x90\x8e\xe9\xa1\xba\xe5\xba\x8f\xe7\xa1\xae\xe5\xae\x9a\xe5\x90\x8d\xe6\xac\xa1\xe3\x80\x82', '\xe7\xa7\xaf\xe5\x88\x86\xe4\xbd\x8e\xe4\xba\x8e\xe6\xb7\x98\xe6\xb1\xb0\xe5\x88\x86\xe6\x95\xb0\xe7\xba\xbf\xe4\xbc\x9a\xe8\xa2\xab\xe6\xb7\x98\xe6\xb1\xb0\xef\xbc\x8c\xe7\xa7\xb0\xe6\x89\x93\xe7\xab\x8b\xe5\x87\xba\xe5\xb1\x80\xe3\x80\x82', '\xe6\x89\x93\xe7\xab\x8b\xe8\xb5\x9b\xe5\x88\xb6\xe6\x9c\x89\xe5\xb1\x80\xe6\x95\xb0\xe4\xb8\x8a\xe9\x99\x90\xef\xbc\x8c\xe6\x89\x93\xe6\xbb\xa1\xe5\xb1\x80\xe6\x95\xb0\xe4\xbc\x9a\xe7\xad\x89\xe5\xbe\x85\xe4\xbb\x96\xe4\xba\xba\xe3\x80\x82', '\xe6\x89\x93\xe7\xab\x8b\xe9\x98\xb6\xe6\xae\xb5\xef\xbc\x8c\xe8\xbd\xae\xe7\xa9\xba\xe6\x97\xb6\xe4\xbc\x9a\xe8\xae\xb01\xe5\xb1\x80\xe6\xb8\xb8\xe6\x88\x8f\xe3\x80\x82', '\xe5\xae\x9a\xe5\xb1\x80\xe8\xb5\x9b\xe5\x88\xb6\xef\xbc\x8c\xe6\x8c\x87\xe6\x89\x93\xe5\x9b\xba\xe5\xae\x9a\xe5\xb1\x80\xe6\x95\xb0\xe5\x90\x8e\xe6\x8c\x89\xe7\xa7\xaf\xe5\x88\x86\xe6\x8e\x92\xe5\x90\x8d\xe3\x80\x82', '\xe6\xaf\x8f\xe5\xb1\x80\xe4\xbc\x9a\xe6\x8c\x89\xe7\x85\xa7\xe5\xbc\x80\xe5\xb1\x80\xe6\x97\xb6\xe7\x9a\x84\xe5\xba\x95\xe5\x88\x86\xe7\xbb\x93\xe7\xae\x97\xe3\x80\x82', '\xe6\xaf\x94\xe8\xb5\x9b\xe6\xb5\x81\xe5\xb1\x80\xe6\x97\xb6\xef\xbc\x8c\xe5\x8f\xaf\xe8\x83\xbd\xe4\xbc\x9a\xe6\x9c\x89\xe7\xa7\xaf\xe5\x88\x86\xe6\x83\xa9\xe7\xbd\x9a\xe3\x80\x82'], 'interval': 5}}, 'maxCoin': (-1), 'maxCoinQS': (-1), 'maxLevel': (-1), 'minCoin': (-1), 'minCoinQS': (-1), 'name': '\xe9\x80\x94\xe6\xb8\xb8\xe9\x98\xbf\xe9\x87\x8c\xe8\xb5\x9b', 'playDesc': '', 'playMode': 'happy', 'robotUserCallUpTime': 10, 'robotUserMaxCount': 0, 'robotUserOpTime': [5, 12], 'roomFee': 45, 'roomMutil': 50, 'sendCoupon': 0, 'showCard': 0, 'tableConf': {'autochange': 1, 'basebet': 1, 'basemulti': 1, 'cardNoteChip': 500, 'canchat': 0, 'coin2chip': 1, 'grab': 1, 'gslam': 128, 'lucky': 0, 'maxSeatN': 3, 'optime': 20, 'passtime': 5, 'rangpaiMultiType': 1, 'robottimes': 1, 'tbbox': 0, 'unticheat': 1}, 'typeName': 'big_match', 'winDesc': ''}

class MyRoom(object, ):

    def __init__(self, roomId):
        pass

class MyStage(MatchStage, ):

    def __init__(self, stageConf):
        pass

    def start(self):
        pass

    def kill(self, reason):
        pass

    def finish(self, reason):
        pass

    def processStage(self):
        pass

class MatchFactoryTest(MatchFactory, ):

    def newStage(self, stageConf):
        """
        创建阶段
        """
        pass

    def newPlayer(self, signer):
        """
        创建一个Player
        """
        pass

def buildMatchMaster(roomId, matchId, matchConf):
    pass

def buildMatchArea(roomId, matchId, matchConf, master):
    pass
CLIENT_IDS = ['Android_3.372_tuyoo.weakChinaMobile.0-hall7.ydmm.happyxinchun', 'Winpc_3.70_360.360.0-hall8.360.texas', 'Android_3.72_tyOneKey,tyAccount,tyGuest.tuyoo.0-hall8.duokunew.day', 'Android_3.363_pps.pps,weakChinaMobile,woStore,aigame.0-hall6.pps.dj']

class MatchChecker(HeartbeatAble, ):

    def __init__(self, master, areas, signerInfoLoader):
        pass

    def _doHeartbeat(self):
        pass

    def _isAllReady(self):
        pass

    def _signinToMatch(self, area, userIds):
        pass

def loadRoomInfo(gameId, roomId):
    pass

def saveRoomInfo(gameId, roomInfo):
    pass

def removeRoomInfo(gameId, roomId):
    pass
if (__name__ == '__main__'):
    ftlog.initLog('groupmatch.log', './logs/')
    matchId = 6057
    masterRoomId = 60571
    areaRoomIds = [60571]
    roominfo.saveRoomInfo = saveRoomInfo
    roominfo.removeRoomInfo = removeRoomInfo
    roominfo.loadRoomInfo = loadRoomInfo
    matchConf = MatchConfig.parse(6, 60571, 6057, '\xe6\xbb\xa13\xe4\xba\xba\xe5\xbc\x80\xe8\xb5\x9b', match_conf['matchConf'])
    signerInfoLoader = SignerInfoLoaderTest()
    areas = []
    master = buildMatchMaster(masterRoomId, matchId, matchConf)
    for areaRoomId in areaRoomIds:
        area = buildMatchArea(areaRoomId, matchId, matchConf, master)
        areas.append(area)
        master.addArea(area)
    master.startHeart()
    MatchChecker(master, areas, signerInfoLoader).startHeart()
    reactor.mainloop()