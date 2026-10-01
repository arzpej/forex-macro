# -*- coding: utf-8 -*-
"""
Created on Thu Oct  1 19:35:20 2026

@author: anism
"""

import pandas as pd

def clean_fed():
    df = pd.read_csv("data/raw/fred_raw.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")   # "." becomes empty
    df = df.dropna()
    df = df.pivot_table(index="date", columns="name", values="value")  # one column per indicator
    df = df.resample("MS").last().ffill()                               # one row per month
    df.to_csv("data/clean/fred_clean.csv")
    return df
 