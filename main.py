import httpx

PASSIVES_URL = "https://www.pathofexile.com/character-window/get-passive-skills?character={character}&accountName={account}"


def fetch_passives(account: str, character) -> dict:
    passives_for_profile_url = PASSIVES_URL.format(character=character, account=account)
    response = httpx.get(
        passives_for_profile_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0"
        },
    )
    # can return 404 "{'error': {'code': 1, 'message': 'Resource not found'}}"
    return response.json()


print(fetch_profile("aaaaroxalot", "HodorHeist"))
