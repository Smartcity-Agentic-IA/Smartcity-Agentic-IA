# schemas.py
from pydantic import BaseModel, Field, condecimal, constr
from typing import Optional
from datetime import datetime

class SensorMessage(BaseModel):
    sensor_id: constr(min_length = 1)
    type: constr(min_length = 1)          # "light", "waste", "traffic", "water"
    value: float
    unit: Optional[str] = None
    latitude: float
    longitude: float
    timestamp: datetime
    status: Optional[str] = None
