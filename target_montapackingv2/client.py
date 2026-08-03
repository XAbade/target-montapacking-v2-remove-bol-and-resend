from hotglue_singer_sdk.target_sdk.client import HotglueSink
from base64 import b64encode
import json
from datetime import datetime
import requests
from hotglue_singer_sdk.exceptions import RetriableAPIError, FatalAPIError
from hotglue_etl_exceptions import InvalidPayloadError
from hotglue_etl_exceptions import InvalidCredentialsError


class MontapackingSink(HotglueSink):

    api_version = "v23_1"

    @property
    def base_url(self) -> str:
        base_url = f"https://api-v6.monta.nl/"
        return base_url
    
    @property
    def authenticator(self):
        user = self.config.get("username")
        passwd = self.config.get("password")
        token = b64encode(f"{user}:{passwd}".encode()).decode()
        return f"Basic {token}"

    @property
    def http_headers(self):
        auth_credentials = {
            "Authorization": self.authenticator
        }
        return auth_credentials

    def validate_input(self, record: dict):
        return self.unified_schema(**record).dict()

    def parse_json(self, input):
        # if it's a string, use json.loads, else return whatever it is
        if isinstance(input, str):
            return json.loads(input)
        return input

    def convert_datetime(self, date: datetime):
        # convert datetime.datetime into str
        if isinstance(date, datetime):
            # This is the format -> "2022-08-15T19:16:35Z"
            return date.strftime("%Y-%m-%dT%H:%M:%SZ")
        return date


    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response."""
        if response.status_code in [429] or 500 <= response.status_code < 600:
            msg = self.response_error_message(response)
            raise RetriableAPIError(msg, response)
        elif response.status_code == 400 and "InvalidReasons" in response.text:
            raise InvalidPayloadError(response.text)
        elif response.status_code == 401 and "Unauthorized" in response.text:
            raise InvalidCredentialsError(response.text)
        elif 400 <= response.status_code < 500:
            try:
                msg = response.text
            except:
                msg = self.response_error_message(response)
            raise FatalAPIError(msg)

