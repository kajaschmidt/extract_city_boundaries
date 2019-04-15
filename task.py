#!/usr/bin/env python
# coding: utf-8

# Imports
import pandas as pd
from functions import generate_GeoJSON, process_citiesCSV

# Note: all data and database files should be saved under "./data/"

# Load input material
citiesDF = pd.read_csv("./data/cities.csv", encoding="utf-8", sep=";")
countries = ["FR", "ES", "SE", "DE", "FI", "NO", "PL", "IT", "GB", "RO", "BY", "GR", "BG", "IS", "PT", "CZ", "DK", "HU", "RS", "AT", "IE", "LT", "LV", "HR", "BA", "SK", "EE", "NL", "CH", "MD", "BE", "AL", "MK", "SI", "ME", "CY", "LU", "FO", "AD", "MT", "LI", "GG", "SM", "GI", "MC", "VA", "CA", "US"]

# Process citiesDF
geoDF = process_citiesCSV(citiesDF, countries)

# Generate .geojson file for a country
# See database references in "DB.json"
country = "BE" # Replace with any country from "countries" list
generate_GeoJSON(country, geoDF)
