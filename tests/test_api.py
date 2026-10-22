import hashlib
import hmac
import time
from decimal import Decimal

import requests


station_code = "EST001-PALTAS"

secret_key = (
    "b6dcf90d2adc48f52a4a326269b900c72e3b64821761e288dc67f29b05e2a84c"#"14518490e8af62b33540c7b37bf9e6cb70662b55314b41dc6ad004020a559ede"#"ae30b1d4e9ea6d8a5b49d59743f9d9434edeb6a28c3d667c62a0887f9adf660e"#"6cbdbcf94e6840bfa01f40f1b7fef761427d3b1fed72d5e27b0e7e052c125ce5"
)


def normalize(value):
    if value is None:
        return "NA"

    text = format(Decimal(str(value)), "f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    return text


def build_message(
    station_code: str,
    payload: dict
) -> str:

    parts = [

        station_code,

        str(payload["timestamp"]),


        normalize(payload.get("battery_level"))

    ]

    for measurement in payload["measurements"]:

        parts.append(
            measurement["sensor_code"]
        )

        parts.append(
            str(measurement["value"])
        )

    return "|".join(parts)


payload = {

    "timestamp": int(time.time()),

    "latitude": -12.123456,

    "longitude": -77.123456,

    "battery_level": 80.3,
    "measurements": [

        {
            "sensor_code": "ambient_temperature",
            "value": 20.0
        },

        {
            "sensor_code": "ambient_humidity",
            "value": 81.5
        },

        {
            "sensor_code": "atmospheric_pressure",
            "value": 1011.5
        },

        {
            "sensor_code": "soil_temperature",
            "value": 24.1
        },

        {
            "sensor_code": "soil_moisture",
            "value": 36.4
        },

        {
            "sensor_code": "soil_ph",
            "value": 6.5
        }

    ],

    "events": [

        {
            "event_type": "Alerta",
            "message": "temperatura",
            "event_code": "201"
        }

    ]

}


message = build_message(
    station_code,
    payload
)

print("MESSAGE:")
print(message)


signature = hmac.new(

    secret_key.encode(),

    message.encode(),

    hashlib.sha256

).hexdigest()

print("SIGNATURE:")
print(signature)


headers = {

    "Signature": signature

}


response = requests.post(

    #f"https://proyectos-didt.inictel-uni.edu.pe/api/palta/v1/stations/{station_code}/measurements",
    f"http://127.0.0.1:8000/api/v1/stations/{station_code}/measurements",

    json=payload,

    headers=headers

)


print("STATUS:", response.status_code)

print("BODY:")
print(response.text)