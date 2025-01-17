# -*- coding: utf-8 -*-
"""
Created on 2015-5-12
@author: zqh
"""
import freetime.util.log as ftlog
from poker.resource import getResourcePath
from poker.util import fsutils
pc2prov_map = {10: '\xe5\x8c\x97\xe4\xba\xac', 20: '\xe4\xb8\x8a\xe6\xb5\xb7', 30: '\xe5\xa4\xa9\xe6\xb4\xa5', 40: '\xe9\x87\x8d\xe5\xba\x86', 1: '\xe5\x86\x85\xe8\x92\x99\xe5\x8f\xa4', 3: '\xe5\xb1\xb1\xe8\xa5\xbf', 5: '\xe6\xb2\xb3\xe5\x8c\x97', 11: '\xe8\xbe\xbd\xe5\xae\x81', 13: '\xe5\x90\x89\xe6\x9e\x97', 15: '\xe9\xbb\x91\xe9\xbe\x99\xe6\xb1\x9f', 21: '\xe6\xb1\x9f\xe8\x8b\x8f', 23: '\xe5\xae\x89\xe5\xbe\xbd', 25: '\xe5\xb1\xb1\xe4\xb8\x9c', 31: '\xe6\xb5\x99\xe6\xb1\x9f', 33: '\xe6\xb1\x9f\xe8\xa5\xbf', 35: '\xe7\xa6\x8f\xe5\xbb\xba', 41: '\xe6\xb9\x96\xe5\x8d\x97', 43: '\xe6\xb9\x96\xe5\x8c\x97', 45: '\xe6\xb2\xb3\xe5\x8d\x97', 51: '\xe5\xb9\xbf\xe4\xb8\x9c', 53: '\xe5\xb9\xbf\xe8\xa5\xbf', 55: '\xe8\xb4\xb5\xe5\xb7\x9e', 57: '\xe6\xb5\xb7\xe5\x8d\x97', 61: '\xe5\x9b\x9b\xe5\xb7\x9d', 65: '\xe4\xba\x91\xe5\x8d\x97', 71: '\xe9\x99\x95\xe8\xa5\xbf', 73: '\xe7\x94\x98\xe8\x82\x83', 75: '\xe5\xae\x81\xe5\xa4\x8f', 81: '\xe9\x9d\x92\xe6\xb5\xb7', 83: '\xe6\x96\xb0\xe7\x96\x86', 85: '\xe8\xa5\xbf\xe8\x97\x8f', 99: '\xe9\xa6\x99\xe6\xb8\xaf'}
prov2pc_map = {}
for (k, v) in pc2prov_map.items():
    prov2pc_map[v] = k

class ContradictError(Exception, ):

    def __init__(self, value):
        pass

    def __str__(self):
        pass

class CoarseError(Exception, ):

    def __init__(self, value):
        pass

    def __str__(self):
        pass
_trie = None

def _initialize():
    pass

def _insert(t):
    pass

def _deredundant(triedict):
    pass

def _common(prefix, triedict):
    pass

def find(phonestr):
    pass