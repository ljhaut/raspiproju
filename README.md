# Electrical home systems manager

This electrical home systems manager is done utilizing a raspberry pi. The software gathers information about the day-ahead prices of electricity through ENTSO-e API and looks for the cheapest hours of the day. During these hours, which typically are during night time, different electrical systems at home are turned on.

The software controls relays that are connected to the raspberry pi through raspberry pi picos. Using the picos makes the system more scalable.
