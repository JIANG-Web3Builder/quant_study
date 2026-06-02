#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insight playback demos that passed with the current account."""

from datetime import datetime

from insight_config import login as insight_login
from insight_python.com.insight import common
from insight_python.com.insight.market_service import market_service
from insight_python.com.insight.playback import *


def playback_tick_demo():
    htsc_code = ["601688.SH", "000014.SZ"]
    start_time = datetime.strptime("2022-04-20 09:00:00", "%Y-%m-%d %H:%M:%S")
    stop_time = datetime.strptime("2022-04-20 15:00:00", "%Y-%m-%d %H:%M:%S")
    playback_tick(htsc_code=htsc_code, replay_time=[start_time, stop_time], fq="pre")


def playback_trans_and_order_demo():
    htsc_code = ["601688.SH", "000014.SZ"]
    start_time = datetime.strptime("2022-04-20 09:00:00", "%Y-%m-%d %H:%M:%S")
    stop_time = datetime.strptime("2022-04-20 15:00:00", "%Y-%m-%d %H:%M:%S")
    playback_trans_and_order(htsc_code=htsc_code, replay_time=[start_time, stop_time], fq="none")


class insightmarketservice(market_service):
    def on_playback_tick(self, result):
        print(result)

    def on_playback_trans_and_order(self, result):
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
    common.fini()


def main():
    get_version()
    login()
    config(False, False, False)
    fini()


if __name__ == "__main__":
    main()
