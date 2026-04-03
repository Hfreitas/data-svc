from datetime import date, datetime, time
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


class AppJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, (datetime, date, time)):
            return o.isoformat()

        if isinstance(o, Decimal):
            return float(o)

        return super().default(o)