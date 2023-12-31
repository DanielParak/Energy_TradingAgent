import config
from scenario import Scenario

import pandas as pd
import datetime as dt

class Market():
    """
    Contains the market model, including market prices at different times, and handles offers placed by the agent
    """

    def __init__(self, sc : Scenario) -> None:
        self.scenario = sc

        self.time_index = 0
        self.current_time = self.scenario.t_start

        # read in price data
        self.prices_DA = pd.read_csv(config.DAY_AHEAD_PATH, sep=";")
        self.prices_IA = pd.read_csv(config.INTRADAY_AUCTION_PATH, sep=";")
        self.prices_IC = pd.read_csv(config.INTRADAY_CONTINUOUS_PATH, sep=";")

        # slice DataFrame to the relevant sequence from start to end from config
        self.prices_DA = self.prices_DA.loc[self.prices_DA["Time"] >= self.scenario.t_start_str]
        self.prices_DA.reset_index(drop=True, inplace=True)

        self.prices_IA = self.prices_IA.loc[self.prices_IA["Time"] >= self.scenario.t_start_str]
        self.prices_IA.reset_index(drop=True, inplace=True)

        self.prices_IC = self.prices_IC.loc[self.prices_IC["Time"] >= self.scenario.t_start_str]
        self.prices_IC.reset_index(drop=True, inplace=True)

        # transform prices to [€/kWh]
        for i in range(len(self.prices_DA)):
            self.prices_DA.at[i, "Price"] = self.prices_DA["Price"][i] / 1000
        for i in range(len(self.prices_IA)):
            self.prices_IA.at[i, "Price"] = self.prices_IA["Price"][i] / 1000
            self.prices_IC.at[i, "Price"] = self.prices_IC["Price"][i] / 1000

    def getMarketPrices(self) -> dict:
        """
        Gives the current market prices as a dictionary.
        The keys are the different markets
        and the values are the respective market prices
        """
        
        result = dict()
        result["DA"] = self.prices_DA["Price"][self.time_index // 4]
        result["IA"] = self.prices_IA["Price"][self.time_index]
        result["IC"] = self.prices_IC["Price"][self.time_index]
        self.time_index += 1
        self.current_time = self.current_time + config.T_DELTA
        return result

    def place_offer(self, offer) -> bool:
        """
        Places an offer on the given market with the respective specifications.
        These include the market (DA, ...), the delivery time, the quantity and the offer price
        :param offer: the offer to be placed
        """

        res = True
        market, del_time, quantity, _ = offer
        compare_time = self.current_time - config.T_DELTA # to correct for the prices that have already been observed in the current time period

        if(quantity < self.scenario.min_offer_quantity):
            res = False
        
        # check gate closure time
        if(market == "DA"):
            closure_config = self.scenario.day_ahead_closure
            closure_time = del_time - dt.timedelta(days = 1)
            closure_time = closure_time.replace(hour = closure_config.hour, minute = closure_config.minute, second = closure_config.second)
            if(closure_time < compare_time):
                res = False

        if(market == "IA"):
            closure_config = self.scenario.intraday_auction_closure
            closure_time = del_time - dt.timedelta(days = 1)
            closure_time = closure_time.replace(hour = closure_config.hour, minute = closure_config.minute, second = closure_config.second)
            if(closure_time < compare_time):
                res = False

        if(market == "IC"):
            if(del_time <= compare_time):
                res = False

        return res


class Household():
    """
    Models the state of the household of the agent, including the battery and the pv system
    """

    def __init__(self, sc : Scenario) -> None:
        self.scenario = sc

        self.time_index = 0

        # read in load data
        self.load = pd.read_csv(config.LOAD_RESIDENTIAL_PATH, sep=";")
        self.load.rename(columns={"Sum [kWh]": "Load"}, inplace=True)
        self.load = self.load.loc[self.load["Time"] >= self.scenario.t_start_str]
        self.load.reset_index(drop=True, inplace=True)

        # scale load data
        for i in range(len(self.load)):
            self.load.at[i, "Load"] = self.load["Load"][i] * self.scenario.load_multiplier

        # read in PV data
        self.pv = pd.read_csv(config.PV_PATH, sep=";")
        self.pv.rename(columns={"pv": "Amount"}, inplace=True)
        self.pv = self.pv.loc[self.pv["Time"] >= self.scenario.t_start_str]
        self.pv.reset_index(drop=True, inplace=True)

        # scale PV data
        for i in range(len(self.pv)):
            self.pv.at[i, "Amount"] = self.pv["Amount"][i] * self.scenario.pv_power_stc
        
    def getPV(self) -> float:
        """
        :return: the PV generation data known to the agent at the current time
        """

        result = self.pv["Amount"][self.time_index]
        self.time_index += 1

        return result
    
    def getLoad(self) -> float:
        """
        :return: current base load
        """
        
        result = self.load["Load"][self.time_index]
        return result
