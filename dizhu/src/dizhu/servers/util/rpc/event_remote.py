# coding=UTF-8
'''事件RPC
'''
from dizhu.entity.treasure_chest.events import TreasureChestEvent
from dizhu.gameplays.game_events import MyFTFinishEvent
from dizhu.replay.replay_service import ReplayViewEvent
from dizhucomm.entity.events import UserTableCallEvent
from poker.entity.configure import gdata
from poker.entity.events.tyevent import GameOverEvent
from poker.protocol.rpccore import markRpcCall


@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def publishUserTableCallEvent(gameId, userId, roomId, tableId, call, isTrueGrab):
    eventBus = gdata.games()[gameId].getEventBus()
    if eventBus:
        eventBus.publishEvent(UserTableCallEvent(gameId, userId, roomId,
                                                 tableId, call, isTrueGrab))
    return 1

@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def publishReplayViewEvent(gameId, userId, videoId):
    eventBus = gdata.games()[gameId].getEventBus()
    if eventBus:
        eventBus.publishEvent(ReplayViewEvent(gameId, userId, videoId))
        
@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def publishMyFTFinishEvent(gameId, userId, roomId, tableId, ftId):
    eventBus = gdata.games()[gameId].getEventBus()
    if eventBus:
        eventBus.publishEvent(MyFTFinishEvent(gameId, userId, roomId, tableId, ftId))

@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def publishGameOverEvent(userId, gameId, clientId, roomId, tableId, gameResult, roomLevel):
    from hall.game import TGHall
    eventBus = TGHall.getEventBus()
    if eventBus:
        eventBus.publishEvent(GameOverEvent(userId, gameId, clientId, roomId, tableId, gameResult, roomLevel))

@markRpcCall(groupName="userId", lockName="userId", syncCall=1)
def publishTreasureChestEvent(gameId, userId, rewardType, rewards, **kwargs):
    from dizhu.game import TGDizhu
    eventBus = TGDizhu.getEventBus()
    if eventBus:
        eventBus.publishEvent(TreasureChestEvent(gameId, userId, rewardType, rewards, **kwargs))
