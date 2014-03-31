#!/usr/bin/env python

import json,re,sys

class Util:

    @staticmethod
    def list2tsv(list):
        return "\t".join(["%s"%item for item in list])

    @staticmethod
    def obj2json(obj):
        return json.dumps(obj, sort_keys=True, separators=(',',':'))

    @staticmethod
    def obj2jslim(obj):
        return Util.obj2json(obj).replace('"', '').replace(', ','\xff').replace(',',' ').replace('\xff',', ')

