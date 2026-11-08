# Public input data

`seattle-weather.csv` contains the first seven daily rows, 2012-01-01 through
2012-01-07, copied unchanged from the public
[Vega Seattle weather CSV](https://github.com/vega/vega-datasets/blob/main/data/seattle-weather.csv).
The upstream dataset describes Seattle weather from 2012 through 2015 and credits
Jason Baldridge's Seattle weather visualization. These are historical public data,
not generated measurements. CI never downloads a live data source.

Fields: date, precipitation, maximum temperature, minimum temperature, wind, weather
category. The lab preserves the supplied values and does not claim to verify units
or instrument calibration. The small excerpt has one row per day. The repository's
MIT license applies to its code; upstream data attribution is retained here.
