# -*- coding: utf-8 -*-
"""
Created on 2016年11月11日

修复比赛LED显示的问题
@author: zhaoliang
"""
from poker.entity.dao import userdata

def buildLedInfo(self, userId, rank, rankRewards):
    """
    构建LED信息
    """
    pass
from poker.entity.game.rooms.quick_upgrade_match_ctrl.match import QUMatch
QUMatch.buildLedInfo = buildLedInfo