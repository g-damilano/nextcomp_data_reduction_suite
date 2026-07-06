from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ISO14126ChannelPolicy:
    require_load_channel: bool = True
    allow_extension_channel: bool = True
    min_strain_channels: int = 2
    allow_additional_strain_channels: bool = True
