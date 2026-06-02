#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extra Insight demos that passed with the current market-data account."""

from insight_python.com.insight import common
from insight_python.com.insight.market_service import market_service
from insight_python.com.insight.subscribe import *


def subscribe_htsc_margin_by_id_demo():
    htsc_code = ["000001.SZ", "000002.SZ"]
    data_type = "security_lending"
    mode = "coverage"
    subscribe_htsc_margin_by_id(htsc_code=htsc_code, data_type=data_type, mode=mode)


def subscribe_htsc_margin_by_type_demo():
    security_type = ["stock"]
    data_type = "security_lending"
    mode = "coverage"
    subscribe_htsc_margin_by_type(security_type=security_type, data_type=data_type, mode=mode)


def subscribe_news_by_id_demo():
    htsc_code = ["360036.SH"]
    mode = "add"
    subscribe_news_by_id(htsc_code=htsc_code, mode=mode)


def subscribe_news_by_type_demo():
    query = [("XSHG", "stock"), ("XSHE", "stock")]
    mode = "coverage"
    subscribe_news_by_type(query=query, mode=mode)


def subscribe_future_kline_by_type_demo():
    query = [("CCFX", "future"), ("XSGE", "future")]
    frequency = ["15s", "1min"]
    mode = "add"
    subscribe_kline_by_type(query=query, frequency=frequency, mode=mode)


class insightmarketservice(market_service):
    def on_subscribe_news(self, result):
        print(result)

    def on_subscribe_htsc_margin(self, result):
        print(result)

    def on_subscribe_kline(self, result):
        print(result)


def fini():
    common.fini()
