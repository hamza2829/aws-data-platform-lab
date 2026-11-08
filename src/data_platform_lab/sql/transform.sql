SELECT
    CAST(date AS DATE) AS date,
    CAST(precipitation AS DECIMAL(10, 1)) AS precipitation,
    CAST(temp_max AS DECIMAL(5, 1)) AS temp_max,
    CAST(temp_min AS DECIMAL(5, 1)) AS temp_min,
    CAST(wind AS DECIMAL(5, 1)) AS wind,
    LOWER(TRIM(weather)) AS weather,
    CAST(temp_max AS DECIMAL(5, 1)) - CAST(temp_min AS DECIMAL(5, 1)) AS temperature_range
FROM raw_input
ORDER BY date
