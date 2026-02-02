from gateway.app.safety import SafetyChecker


def test_denylist_blocks() -> None:
    checker = SafetyChecker(max_tokens_cap=128, denylist_words=["banword"])
    payload = {"messages": [{"role": "user", "content": "This has banword."}]}
    result = checker.check(payload)
    assert not result.allowed
    assert result.reason == "denylist"


def test_max_tokens_capped() -> None:
    checker = SafetyChecker(max_tokens_cap=64, denylist_words=[])
    payload = {"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 256}
    result = checker.check(payload)
    assert result.allowed
    assert result.adjusted_max_tokens == 64
