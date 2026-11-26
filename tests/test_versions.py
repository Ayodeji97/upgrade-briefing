import pytest

from upgrade_briefing.versions import is_version, parse_version


def test_parses_stable_and_prerelease():
    assert str(parse_version("2.7.0")) == "2.7.0"
    v = parse_version("2.7.0-rc03")
    assert (v.major, v.minor, v.patch, v.channel, v.pre_num) == (2, 7, 0, "rc", 3)
    assert not v.is_stable


def test_release_order():
    ordered = ["2.6.1", "2.7.0-alpha01", "2.7.0-alpha12", "2.7.0-beta01", "2.7.0-rc03", "2.7.0", "2.10.0"]
    keys = [parse_version(v).key for v in ordered]
    assert keys == sorted(keys)


def test_double_digit_minor_sorts_numerically_not_as_text():
    # As strings "2.10.0" < "2.9.0"; as version keys it must be greater.
    assert parse_version("2.10.0").key > parse_version("2.9.0").key


def test_rejects_non_versions():
    assert not is_version("gradle-plugin")
    with pytest.raises(ValueError):
        parse_version("Version 2.7.0")
