#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insight subscription demos that passed with the current account."""

from insight_config import login as insight_login
from insight_python.com.insight import common, subscribe
from insight_python.com.insight.market_service import market_service
from insight_python.com.insight.subscribe import *
from insight_python.com.interface.mdc_gateway_base_define import GateWayServerConfig


def subscribe_tick_by_type_demo():
    query = [("XSHG", "stock"), ("XSHE", "stock")]
    subscribe_tick_by_type(query=query, mode="add")


def subscribe_kline_by_type_demo():
    query = [("XSHG", "stock"), ("XSHE", "stock")]
    subscribe_kline_by_type(query=query, frequency=["15s", "1min"], mode="add")


def subscribe_trans_and_order_by_type_demo():
    query = [("XSHG", "stock"), ("XSHE", "stock")]
    subscribe_trans_and_order_by_type(query=query, mode="coverage")


def subscribe_tick_by_id_demo():
    htsc_code = ["601688.SH", "603980.SH"]
    subscribe_tick_by_id(htsc_code=htsc_code, mode="add")


def subscribe_kline_by_id_demo():
    htsc_code = ["601688.SH", "000001.SZ"]
    subscribe_kline_by_id(htsc_code=htsc_code, frequency=["15s", "1min"], mode="add")


def subscribe_trans_and_order_by_id_demo():
    htsc_code = ["601688.SH", "603980.SH"]
    subscribe_trans_and_order_by_id(htsc_code=htsc_code, mode="add")


def subscribe_derived_demo():
    subscribe_derived(
        type="north_bound",
        htsc_code=["SCHKSBSH.HT", "SCHKSBSZ.HT", "SCSHNBHK.HT", "SCSZNBHK.HT"],
        frequency="1min",
        mode="coverage",
    )


class insightmarketservice(market_service):
    def on_subscribe_tick(self, result):
        print(result)

    def on_subscribe_kline(self, result):
        print(result)

    def on_subscribe_trans_and_order(self, result):
        print(result)

    def on_subscribe_derived(self, result):
        print(result)


def login():
    markets = insightmarketservice()
    result = insight_login(markets, common_module=common, login_log=False)
    print(result)


def config(open_trace=True, open_file_log=True, open_cout_log=True):
    common.config(open_trace, open_file_log, open_cout_log)


def get_version():
    print(common.get_version())


def fini():
    if GateWayServerConfig.IsRealTimeData:
        subscribe.sync()
    common.fini()


def main():
    get_version()
    login()
    config(False, False, False)
    fini()


if __name__ == "__main__":
    main()
