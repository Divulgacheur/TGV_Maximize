import os
from typing import get_type_hints, Union

from dotenv import load_dotenv,set_key

load_dotenv()

def dict_cookie_from_str(str_cookies):
    d_cookies = {}
    l_cookies = str_cookies.split("; ")
    for key_item in l_cookies:
        i = key_item.find("=")
        key = key_item[:i]
        item = key_item[i+1:]
        d_cookies[key] = item
    return d_cookies

def str_cookies_from_dict(d_cookies):
    str_cookie = ""
    for key, item in d_cookies.items():
        str_cookie += key + "="+ item + "; "
    str_cookie = str_cookie[:-2]
    return str_cookie

class AppConfigError(Exception):
    """
    Exception for config errors.
    """


def _parse_bool(val: Union[str, bool]) -> bool:  # pylint: disable=E1136
    return val if isinstance(val, bool) else val.lower()


class AppConfig:
    """
    Application configuration.
    """

    SNCFCONNECT_COOKIE: str

    """
    Map environment variables to class fields according to these rules:
      - Field won't be parsed unless it has a type annotation
      - Field will be skipped if not in all caps
      - Class field and environment variable name are the same
    """

    def __init__(self, env):
        for field in AppConfig.__annotations__:
            if not field.isupper():
                continue

            # Raise AppConfigError if required field not supplied
            default_value = getattr(self, field, None)
            if default_value is None and env.get(field) is None:
                raise AppConfigError(f'The {field} field is required in the .env file')

            # Cast env var value to expected type and raise AppConfigError on failure

            var_type = get_type_hints(AppConfig)[field]
            try:
                if var_type == bool:
                    value = _parse_bool(env.get(field, default_value))
                else:
                    value = var_type(env.get(field, default_value))

                self.__setattr__(field, value)
            except ValueError:
                raise AppConfigError(f'Unable to cast value of "{env[field]}" '
                                     f'to type "{var_type}" for "{field}" field') from None

    def __repr__(self):
        return str(self.__dict__)

    def update_cookies_from_dict(self, field, str_cookies):
        str_old = self.__dict__[field]
        d_new_cookies = str_old
        print('old-new',d_new_cookies, str_cookies)
        set_key('.env',field, str_cookies)


# Expose Config object for app to import
Config = AppConfig(os.environ)
