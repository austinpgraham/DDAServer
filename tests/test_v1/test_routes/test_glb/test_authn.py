import pytest
from http import HTTPStatus
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import TypeAlias
from unittest.mock import patch
from dda.v1.models.user import SessionToken
from dda.v1.schemas.authn import GoogleTokenExchangeDto
from dda.v1.schemas.user import UserCreateDto
from dda.v1.services.authn import AuthNService
from dda.v1.services.authn.google import ExternalGoogleService
from dda.v1.services.authn.google import IGoogleService
from tests.types import APICaller


TEST_OAUTH_RESPONSE_USER = UserCreateDto(
    email="test@email.com",
    family_name="Graham",
    given_name="Austin",
    is_email_verified=True,
    profile_picture="https://fakepic.com/picture.png",
)


TEST_CODE_BODY = {
    "authorizationCode": "someCode",
    "codeVerifier": "verifier",
    "redirectUri": "http://localhost",
}


MockedLoginCallable: TypeAlias = Callable[
    [GoogleTokenExchangeDto], Coroutine[Any, Any, SessionToken]
]


class MockGoogleService(IGoogleService):
    @staticmethod
    async def get_user_profile(gid_token: str) -> UserCreateDto:
        return TEST_OAUTH_RESPONSE_USER

    @staticmethod
    async def exchange_auth_token_for_id_token(
        authorization_code: str, code_verifier: str, redirect_uri: str
    ) -> str:
        return "test_token"


@pytest.fixture
def mocked_google_oauth() -> MockedLoginCallable:
    original_login_with_google = AuthNService.login_with_google

    async def login_with_google_with_mock_fetcher(
        token_exchange_dto: GoogleTokenExchangeDto,
    ) -> SessionToken:
        return await original_login_with_google(token_exchange_dto, MockGoogleService)

    return login_with_google_with_mock_fetcher


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_request_body",
    [
        {"codeVerifier": "test", "redirect_uri": "test"},
        {"authorization_code": "test", "redirect_uri": "test"},
        {"authorization_code": "test", "codeVerifier": "test"},
    ],
)
async def test_google_login_should_return_400_if_attributes_are_missing(
    api_post: APICaller, test_request_body: dict[str, Any]
) -> None:
    session_token_response = await api_post(
        "/v1/glb/auth/google",
        body=test_request_body,
        expected_status_code=HTTPStatus.BAD_REQUEST,
    )
    assert session_token_response.error_code == "ValidationError"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_google_login_should_return_400_when_token_cannot_be_verified(
    api_post: APICaller,
) -> None:
    async def login_with_google_with_exception(
        token_exchange_dto: GoogleTokenExchangeDto,
    ) -> SessionToken:
        raise ExternalGoogleService.TokenValidationException()

    with patch.object(
        AuthNService, "login_with_google", new=login_with_google_with_exception
    ):
        session_token_response = await api_post(
            "/v1/glb/auth/google",
            body=TEST_CODE_BODY,
            expected_status_code=HTTPStatus.BAD_REQUEST,
        )
        assert session_token_response.error_code == "InvalidToken"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_google_login_should_return_400_when_code_cannot_be_exchanged(
    api_post: APICaller,
) -> None:
    async def login_with_google_with_exception(
        token_exchange_dto: GoogleTokenExchangeDto,
    ) -> SessionToken:
        raise ExternalGoogleService.TokenExchangeException()

    with patch.object(
        AuthNService, "login_with_google", new=login_with_google_with_exception
    ):
        session_token_response = await api_post(
            "/v1/glb/auth/google",
            body=TEST_CODE_BODY,
            expected_status_code=HTTPStatus.BAD_REQUEST,
        )
        assert session_token_response.error_code == "TokenExchangeFailed"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_google_login_should_return_201_when_token_is_created(
    api_post: APICaller, mocked_google_oauth: MockedLoginCallable
) -> None:
    with patch.object(AuthNService, "login_with_google", new=mocked_google_oauth):
        session_token_response = await api_post(
            "/v1/glb/auth/google",
            body=TEST_CODE_BODY,
            expected_status_code=HTTPStatus.CREATED,
        )
        assert session_token_response.response["token"] is not None
        assert len(session_token_response.response["token"]) > 0
        assert (
            session_token_response.response["user"]["email"]
            == TEST_OAUTH_RESPONSE_USER.email
        )
        assert (
            session_token_response.response["user"]["familyName"]
            == TEST_OAUTH_RESPONSE_USER.family_name
        )
        assert (
            session_token_response.response["user"]["givenName"]
            == TEST_OAUTH_RESPONSE_USER.given_name
        )
        assert (
            session_token_response.response["user"]["phoneNumber"]
            == TEST_OAUTH_RESPONSE_USER.phone_number
        )
        assert (
            session_token_response.response["user"]["profilePicture"]
            == TEST_OAUTH_RESPONSE_USER.profile_picture
        )


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_google_login_should_return_201_with_replaced_session_when_session_exists(
    api_post: APICaller, mocked_google_oauth: MockedLoginCallable
) -> None:
    with patch.object(AuthNService, "login_with_google", new=mocked_google_oauth):
        # Get a fresh session
        session_token_response = await api_post(
            "/v1/glb/auth/google",
            body=TEST_CODE_BODY,
            expected_status_code=HTTPStatus.CREATED,
        )
        assert session_token_response.response["token"] is not None
        first_token = session_token_response.response["token"]

        # Now try and replace it
        session_token_response = await api_post(
            "/v1/glb/auth/google",
            body=TEST_CODE_BODY,
            expected_status_code=HTTPStatus.CREATED,
        )
        assert session_token_response.response["token"] is not None
        second_token = session_token_response.response["token"]

        assert first_token != second_token
        assert await SessionToken.objects.filter(token=first_token).afirst() is None
