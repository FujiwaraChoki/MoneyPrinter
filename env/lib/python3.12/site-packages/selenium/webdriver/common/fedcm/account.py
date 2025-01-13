# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from enum import Enum
from typing import Optional


class LoginState(Enum):
    SIGN_IN = "SignIn"
    SIGN_UP = "SignUp"


class Account:
    """Represents an account displayed in a FedCM account list.

    See: https://w3c-fedid.github.io/FedCM/#dictdef-identityprovideraccount
         https://w3c-fedid.github.io/FedCM/#webdriver-accountlist
    """

    def __init__(self, account_data):
        self._account_data = account_data

    @property
    def account_id(self) -> Optional[str]:
        return self._account_data.get("accountId")

    @property
    def email(self) -> Optional[str]:
        return self._account_data.get("email")

    @property
    def name(self) -> Optional[str]:
        return self._account_data.get("name")

    @property
    def given_name(self) -> Optional[str]:
        return self._account_data.get("givenName")

    @property
    def picture_url(self) -> Optional[str]:
        return self._account_data.get("pictureUrl")

    @property
    def idp_config_url(self) -> Optional[str]:
        return self._account_data.get("idpConfigUrl")

    @property
    def terms_of_service_url(self) -> Optional[str]:
        return self._account_data.get("termsOfServiceUrl")

    @property
    def privacy_policy_url(self) -> Optional[str]:
        return self._account_data.get("privacyPolicyUrl")

    @property
    def login_state(self) -> Optional[str]:
        return self._account_data.get("loginState")
