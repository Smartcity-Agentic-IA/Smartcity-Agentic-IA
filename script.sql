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




--alerts table

CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  sensor_id TEXT,
  type TEXT,
  severity TEXT,
  reason TEXT,
  value DOUBLE PRECISION,
  expected DOUBLE PRECISION,
  ts TIMESTAMP,
  geom GEOGRAPHY(Point,4326)
);

CREATE INDEX IF NOT EXISTS alerts_ts_idx   ON alerts(ts);
CREATE INDEX IF NOT EXISTS alerts_geom_idx ON alerts USING GIST(geom);


--actions table
CREATE TABLE IF NOT EXISTS actions (
  action_id TEXT PRIMARY KEY,
  action_type TEXT,
  priority TEXT,
  sensor_id TEXT,
  targets TEXT[],
  parameters JSONB,
  ts TIMESTAMP,
  geom GEOGRAPHY(Point,4326),
  reason TEXT
);

CREATE INDEX IF NOT EXISTS actions_ts_idx   ON actions(ts);
CREATE INDEX IF NOT EXISTS actions_geom_idx ON actions USING GIST(geom);



--thresholds table
CREATE TABLE IF NOT EXISTS thresholds (
  type TEXT PRIMARY KEY,           -- 'waste', 'traffic', 'light', 'water'
  rule_name TEXT,                  -- ex: 'dynamic_waste_high'
  threshold_value DOUBLE PRECISION,
  updated_at TIMESTAMP
);
