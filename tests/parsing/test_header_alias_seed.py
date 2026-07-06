from __future__ import annotations

from parsing.columns.family_classifier import classify_channel_family


def test_header_alias_seed_cases_are_recognized() -> None:
    expected = {
        "time": [
            "Time",
            "Time[s]",
            "time",
            "Elapsed",
        ],
        "timestamp": [
            "TIMESTAMP",
            "System Date",
            "DateTime",
        ],
        "record_id": [
            "Scan #",
            "S/No",
            "RECORD",
            "RN",
        ],
        "load": [
            "Force",
            "Load",
            "Load [N]",
            "C_1_Force[kN]",
            "Load on S1-Ch3 kN",
            "Maximum Force",
        ],
        "strain": [
            "strain",
            "tensile strain",
            "Tensile strain (%)",
            "Eng_Strain[]",
            "e_true",
            "Front strain",
            "Rear strain",
            "Uniaxial Gage 1 on S1-Ch2 microstrain",
            "Uniaxial Gage 2 on S1-Ch1 microstrain",
            "dms{i}",
            "exx",
            "eyy",
            "exy",
            "e1",
            "e2",
            "gamma",
        ],
        "stress": [
            "stress",
            "Tensile stress (MPa)",
            "Eng_Stress[MPa]",
            "Sigma_true",
            "node stress",
        ],
        "temperature": [
            "Temp",
            "Temperature[C]",
            "Temp_C_Avg",
        ],
    }

    for family, aliases in expected.items():
        for alias in aliases:
            assert classify_channel_family(alias) == family


def test_displacement_and_extension_aliases_are_split_by_instrument_semantics() -> None:
    expected = {
        "Displacement": "displacement",
        "Displacement [mm]": "displacement",
        "Distance": "displacement",
        "C_1_D\u00e9placement[mm]": "displacement",
        "extension": "extension",
        "Crosshead Separation": "extension",
        "C_1_D\u00e9form1[mm]": "extension",
    }

    for alias, family in expected.items():
        assert classify_channel_family(alias) == family
