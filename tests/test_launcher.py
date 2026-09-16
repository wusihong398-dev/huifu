from huifu.launcher import _self_test


def test_launcher_self_test() -> None:
    assert _self_test() == 0

