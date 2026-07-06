import pytest

from method_binding.channel_resolver import MethodChannelResolver


def test_method_channel_resolver_stub_raises_not_implemented() -> None:
    resolver = MethodChannelResolver()
    with pytest.raises(NotImplementedError):
        resolver.run(parsed_sample=None, policy=None)
