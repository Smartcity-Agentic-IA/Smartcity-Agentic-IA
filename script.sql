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

CREATE TABLE IF NOT EXISTS actions (
  id SERIAL PRIMARY KEY,
  action_id VARCHAR(50) UNIQUE,
  sensor_id VARCHAR(50),
  event_type VARCHAR(100),
  action_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  status VARCHAR(30) DEFAULT 'pending', -- pending / confirmed / rejected
  feedback_by VARCHAR(100),
  feedback_at TIMESTAMPTZ
);



-- Table pour logger les exécutions de l'actuator
CREATE TABLE IF NOT EXISTS actuator_executions (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(50) NOT NULL,
    sensor_id VARCHAR(50),
    result_json JSONB,
    status VARCHAR(20),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (action_id) REFERENCES actions(action_id)
);

CREATE INDEX idx_actuator_executions_action_id ON actuator_executions(action_id);
CREATE INDEX idx_actuator_executions_executed_at ON actuator_executions(executed_at);

-- Vérification
\d actuator_executions