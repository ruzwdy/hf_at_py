# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'HaiFeng'
__mtime__ = '2016/9/13'
"""

import sys
import os
import _thread
from time import sleep

# sys.path.append('..')  #调用父目录下的模块
sys.path.append(os.path.join(sys.path[0], '..'))  # 调用父目录下的模块

from py_ctp.enums import OrderPriceTypeType, DirectionType, OffsetFlagType, HedgeFlagType, TimeConditionType, VolumeConditionType, ContingentConditionType, ForceCloseReasonType, OrderStatusType, ActionFlagType
from py_ctp.structs import CThostFtdcMarketDataField, CThostFtdcRspAuthenticateField, CThostFtdcRspInfoField, CThostFtdcSettlementInfoConfirmField, CThostFtdcInstrumentStatusField, CThostFtdcInputOrderField, CThostFtdcOrderField
from py_ctp.trade import Trade
from py_ctp.quote import Quote


class Test:

    def __init__(self):
        self.Session = ''
        self.q = Quote()
        self.t = Trade()
        self.req = 0
        self.ordered = False
        self.needAuth = False
        self.frontAddr = ''
        self.broker = ''
        self.investor = ''
        self.pwd = ''

    def q_OnFrontConnected(self):
        print('connected')
        self.q.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd)

    def q_OnRspUserLogin(self, rsp, info, req, last):
        print(info)

        # insts = create_string_buffer(b'cu', 5)
        self.q.SubscribeMarketData('rb1805')

    def q_OnTick(self, tick):
        f = CThostFtdcMarketDataField()
        f = tick
        # print(tick)

        if not self.ordered:
            _thread.start_new_thread(self.Order, (f,))
            self.ordered = True

    def Order(self, f):
        print("报单")
        self.req += 1
        self.t.ReqOrderInsert(
            BrokerID=self.broker,
            InvestorID=self.investor,
            InstrumentID=f.getInstrumentID(),
            OrderRef='{0:>12}'.format(self.req),
            UserID=self.investor,
            OrderPriceType=OrderPriceTypeType.LimitPrice,
            Direction=DirectionType.Buy,
            CombOffsetFlag=OffsetFlagType.Open.__char__(),
            CombHedgeFlag=HedgeFlagType.Speculation.__char__(),
            LimitPrice=f.getLastPrice() - 50,
            VolumeTotalOriginal=1,
            TimeCondition=TimeConditionType.GFD,
            # GTDDate=''
            VolumeCondition=VolumeConditionType.AV,
            MinVolume=1,
            ContingentCondition=ContingentConditionType.Immediately,
            StopPrice=0,
            ForceCloseReason=ForceCloseReasonType.NotForceClose,
            IsAutoSuspend=0,
            IsSwapOrder=0,
            UserForceClose=0)

    def OnFrontConnected(self):
        print('connected')
        if self.needAuth:
            self.t.ReqAuthenticate(self.broker, self.investor, '@haifeng', '8MTL59FK1QGLKQW2')
        else:
            self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd, UserProductInfo='@haifeng')

    def OnRspAuthenticate(self, pRspAuthenticateField=CThostFtdcRspAuthenticateField, pRspInfo=CThostFtdcRspInfoField, nRequestID=int, bIsLast=bool):
        print('auth：{0}:{1}'.format(pRspInfo.getErrorID(), pRspInfo.getErrorMsg()))
        self.t.ReqUserLogin(BrokerID=self.broker, UserID=self.investor, Password=self.pwd, UserProductInfo='@haifeng')

    def OnRspUserLogin(self, rsp, info, req, last):
        i = CThostFtdcRspInfoField()
        i = info
        print(i.getErrorMsg())

        if i.getErrorID() == 0:
            self.Session = rsp.getSessionID()
            self.t.ReqSettlementInfoConfirm(BrokerID=self.broker, InvestorID=self.investor)

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm=CThostFtdcSettlementInfoConfirmField, pRspInfo=CThostFtdcRspInfoField, nRequestID=int, bIsLast=bool):
        print(pSettlementInfoConfirm)
        _thread.start_new_thread(self.StartQuote, ())
        _thread.start_new_thread(self.Qry, ())

    def StartQuote(self):
        self.q.CreateApi()
        spi = self.q.CreateSpi()
        self.q.RegisterSpi(spi)

        self.q.OnFrontConnected = self.q_OnFrontConnected
        self.q.OnRspUserLogin = self.q_OnRspUserLogin
        self.q.OnRtnDepthMarketData = self.q_OnTick

        self.q.RegCB()

        self.q.RegisterFront(self.frontAddr.split(',')[1])
        self.q.Init()
        self.q.Join()

    def Qry(self):
        sleep(1.1)
        self.t.ReqQryInstrument()
        while True:
            sleep(1.1)
            self.t.ReqQryTradingAccount(self.broker, self.investor)
            sleep(1.1)
            self.t.ReqQryInvestorPosition(self.broker, self.investor)
            return

    def OnRtnInstrumentStatus(self, pInstrumentStatus=CThostFtdcInstrumentStatusField):
        pass

    def OnRspOrderInsert(self, pInputOrder=CThostFtdcInputOrderField, pRspInfo=CThostFtdcRspInfoField, nRequestID=int, bIsLast=bool):
        print(pRspInfo)
        print(pInputOrder)
        print(pRspInfo.getErrorMsg())

    def OnRtnOrder(self, pOrder=CThostFtdcOrderField):
        # print(pOrder)
        if pOrder.getSessionID() == self.Session and pOrder.getOrderStatus() == OrderStatusType.NoTradeQueueing:
            print("撤单")
            self.t.ReqOrderAction(self.broker, self.investor, InstrumentID=pOrder.getInstrumentID(), OrderRef=pOrder.getOrderRef(), FrontID=pOrder.getFrontID(), SessionID=pOrder.getSessionID(), ActionFlag=ActionFlagType.Delete)

    def OnRspInstrument(self, instrument, last, rspinfo, nreq):
        pass

    def Run(self, front='tcp://180.168.146.187:10000,tcp://180.168.146.187:10010', broker='9999', investor='008105', pwd='1'):
        # CreateApi时会用到log目录,需要在程序目录下创建**而非dll下**
        self.t.CreateApi()
        spi = self.t.CreateSpi()
        self.t.RegisterSpi(spi)

        self.t.OnFrontConnected = self.OnFrontConnected
        self.t.OnRspUserLogin = self.OnRspUserLogin
        self.t.OnRspQryInstrument = self.OnRspInstrument
        self.t.OnRspSettlementInfoConfirm = self.OnRspSettlementInfoConfirm
        self.t.OnRspAuthenticate = self.OnRspAuthenticate
        self.t.OnRtnInstrumentStatus = self.OnRtnInstrumentStatus
        self.t.OnRspOrderInsert = self.OnRspOrderInsert
        self.t.OnRtnOrder = self.OnRtnOrder

        self.t.RegCB()

        self.frontAddr = front
        self.broker = broker
        self.investor = investor
        self.pwd = pwd

        self.t.RegisterFront(self.frontAddr.split(',')[0])
        # self.t.SubscribePrivateTopic(nResumeType=2)  # quick
        # self.t.SubscribePrivateTopic(nResumeType=2)
        self.t.Init()
        # self.t.Join()


if __name__ == '__main__':
    t = Test()
    if len(sys.argv) == 1:
        t.Run()
    else:
        t.Run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    input()