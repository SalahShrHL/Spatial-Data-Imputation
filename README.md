# Spatial Data Imputation using Dead Reckoning and Map Matching

This project is an implementation of a two-step approach for spatial data imputation. The approach combines Dead Reckoning and Map Matching techniques to estimate missing spatial data.

## Description

The project uses two main techniques:

1. **Dead Reckoning**: This is a method of predicting an object's future location based on its current speed, heading, and other known variables. It's often used when precise tracking data is not available.

2. **Map Matching**: This is the process of aligning a sequence of observed user positions with the road network on a digital map. It's used to identify the road, or sequence of roads, that a vehicle is likely to have traveled along.

The project uses the Leuven Map Matching library for the map matching process.
