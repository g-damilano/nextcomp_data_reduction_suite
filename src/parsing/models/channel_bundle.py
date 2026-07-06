from __future__ import annotations

from dataclasses import dataclass, field

from .channel_record import ChannelRecord


@dataclass(slots=True)
class ChannelBundle:
    load_channels: list[ChannelRecord] = field(default_factory=list)
    extension_channels: list[ChannelRecord] = field(default_factory=list)
    strain_channels: list[ChannelRecord] = field(default_factory=list)
    time_channels: list[ChannelRecord] = field(default_factory=list)
    stress_channels: list[ChannelRecord] = field(default_factory=list)
    displacement_channels: list[ChannelRecord] = field(default_factory=list)
    unknown_channels: list[ChannelRecord] = field(default_factory=list)

    def all_channels(self) -> list[ChannelRecord]:
        return (
            self.load_channels
            + self.extension_channels
            + self.strain_channels
            + self.time_channels
            + self.stress_channels
            + self.displacement_channels
            + self.unknown_channels
        )
