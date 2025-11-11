use smartcitydb;

CREATE TABLE sensors_data (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50),
    type VARCHAR(50),
    value DOUBLE PRECISION,
    unit VARCHAR(20),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOGRAPHY(Point, 4326),
    timestamp TIMESTAMP,
    status VARCHAR(20)
);


select * from sensors_data;

