# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Utilities for sequences."""

import random
from typing import Any

from eumos.instance import InstructionInstance

from tibbar.utils import MASK_64_BIT

# IEEE 754 widths (inferred; ieee_pkg no longer exists)
SINGLE_PRE_EXP_W = 8
SINGLE_PRE_MANT_W = 23
DOUBLE_PRE_EXP_W = 11
DOUBLE_PRE_MANT_W = 52


def _pack_float(sign: int, exponent: int, mantissa: int, f64: bool) -> int:
    """Pack sign, exponent, mantissa into 32- or 64-bit float bits."""
    if f64:
        return (
            (sign << 63)
            | ((exponent & ((1 << DOUBLE_PRE_EXP_W) - 1)) << DOUBLE_PRE_MANT_W)
            | (mantissa & ((1 << DOUBLE_PRE_MANT_W) - 1))
        )
    return (
        (sign << 31)
        | ((exponent & ((1 << SINGLE_PRE_EXP_W) - 1)) << SINGLE_PRE_MANT_W)
        | (mantissa & ((1 << SINGLE_PRE_MANT_W) - 1))
    )


class FloatGen:
    """
    Generate randomised float bit patterns (F32/F64) for use by SetFPRs and
    float stress sequences. Parameters: b_* (bool), p_* (probability), w_* (weight dict).
    """

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.random = random.Random()
        self.random.seed(self.tibbar.random.random())

        # Exponent quartiles and limits for F32 and F64 (index 0 = single, 1 = double)
        self.exponent_25_percent_size = [
            1 << (SINGLE_PRE_EXP_W - 2),
            1 << (DOUBLE_PRE_EXP_W - 2),
        ]
        self.exponent_75_percent_size = [
            (1 << (SINGLE_PRE_EXP_W - 1)) + self.exponent_25_percent_size[0],
            (1 << (DOUBLE_PRE_EXP_W - 1)) + self.exponent_25_percent_size[1],
        ]
        self.exponent_special = [
            (1 << SINGLE_PRE_EXP_W) - 1,
            (1 << DOUBLE_PRE_EXP_W) - 1,
        ]
        self.exponent_max_valid = [
            self.exponent_special[0] - 1,
            self.exponent_special[1] - 1,
        ]

        self.mantissa_25_percent_size = [
            1 << (SINGLE_PRE_MANT_W - 2),
            1 << (DOUBLE_PRE_MANT_W - 2),
        ]
        self.mantissa_75_percent_size = [
            (1 << (SINGLE_PRE_MANT_W - 1)) + self.mantissa_25_percent_size[0],
            (1 << (DOUBLE_PRE_MANT_W - 1)) + self.mantissa_25_percent_size[1],
        ]
        self.mantissa_max_valid = [
            (1 << SINGLE_PRE_MANT_W) - 1,
            (1 << DOUBLE_PRE_MANT_W) - 1,
        ]
        self.mantissa_canonical_nan = [
            1 << (SINGLE_PRE_MANT_W - 1),
            1 << (DOUBLE_PRE_MANT_W - 1),
        ]

        self.boxed_value = 0xFFFF_FFFF_0000_0000
        self.reset()

    def reset(self) -> None:
        self.p_negative = 0.5
        self.p_f64 = 0.5
        self.p_boxed = 0.95
        self.w_ftype: dict[str, int] = {"NAN": 1, "INF": 1, "NUM": 10}
        self.w_exponent: dict[str, int] = {
            "MAX": 1,
            "NEAR_MAX": 2,
            "LARGE": 5,
            "MEDIUM": 5,
            "SMALL": 5,
            "NEAR_MIN": 2,
            "MIN": 1,
        }
        self.w_mantissa: dict[str, int] = {
            "MAX": 1,
            "NEAR_MAX": 2,
            "LARGE": 5,
            "MEDIUM": 5,
            "SMALL": 5,
            "NEAR_MIN": 2,
            "MIN": 1,
        }

    def rand_prob(self, parameter: float) -> bool:
        return self.random.random() < parameter

    def rand_range(self, low: int, high: int) -> int:
        if low == high:
            return low
        return self.random.randrange(low, high)

    def rand_weights(self, vals_and_weights: dict[str, int]) -> str:
        return self.random.choices(
            list(vals_and_weights.keys()),
            weights=list(vals_and_weights.values()),
            k=1,
        )[0]

    def gen(self, **kwargs: Any) -> int:
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key.startswith("b_"):
                    assert isinstance(
                        value, bool
                    ), f"{key} is required to be of type bool. Got: {value} ({type(value)})"
                elif key.startswith("p_"):
                    assert isinstance(
                        value, (int, float)
                    ), f"{key} is required to be of type float. Got: {value} ({type(value)})"
                elif key.startswith("w_"):
                    assert isinstance(
                        value, dict
                    ), f"{key} is required to be of type dict. Got: {value} ({type(value)})"
                else:
                    raise AssertionError(
                        f"Trying to set {key} which is not a configurable parameter"
                    )
                setattr(self, key, value)
            else:
                pass  # ignore unknown kwargs

        float_sel = 1 if self.rand_prob(self.p_f64) else 0
        sign = 1 if self.rand_prob(self.p_negative) else 0

        float_type = self.rand_weights(self.w_ftype)
        if float_type in ("NAN", "INF"):
            exponent = self.exponent_special[float_sel]
        else:
            sel_exponent_range = self.rand_weights(self.w_exponent)
            if sel_exponent_range == "MIN":
                exponent = 0
            elif sel_exponent_range == "NEAR_MIN":
                exponent = self.rand_range(1, 4)
            elif sel_exponent_range == "SMALL":
                exponent = self.rand_range(4, self.exponent_25_percent_size[float_sel])
            elif sel_exponent_range == "MEDIUM":
                exponent = self.rand_range(
                    self.exponent_25_percent_size[float_sel],
                    self.exponent_75_percent_size[float_sel],
                )
            elif sel_exponent_range == "LARGE":
                exponent = self.rand_range(
                    self.exponent_75_percent_size[float_sel],
                    self.exponent_max_valid[float_sel] - 3,
                )
            elif sel_exponent_range == "NEAR_MAX":
                exponent = self.rand_range(
                    self.exponent_max_valid[float_sel] - 3,
                    self.exponent_max_valid[float_sel],
                )
            else:
                exponent = self.exponent_max_valid[float_sel]

        if float_type == "INF":
            mantissa = 0
        else:
            sel_mantissa_range = self.rand_weights(self.w_mantissa)
            if sel_mantissa_range == "MIN":
                mantissa = self.mantissa_canonical_nan[float_sel] if float_type == "NAN" else 0
            elif sel_mantissa_range == "NEAR_MIN":
                mantissa = self.rand_range(1, 8)
            elif sel_mantissa_range == "SMALL":
                mantissa = self.rand_range(8, self.mantissa_25_percent_size[float_sel])
            elif sel_mantissa_range == "MEDIUM":
                mantissa = self.rand_range(
                    self.mantissa_25_percent_size[float_sel],
                    self.mantissa_75_percent_size[float_sel],
                )
            elif sel_mantissa_range == "LARGE":
                mantissa = self.rand_range(
                    self.mantissa_75_percent_size[float_sel],
                    self.mantissa_max_valid[float_sel] - 7,
                )
            elif sel_mantissa_range == "NEAR_MAX":
                mantissa = self.rand_range(
                    self.mantissa_max_valid[float_sel] - 7,
                    self.mantissa_max_valid[float_sel],
                )
            else:
                mantissa = self.mantissa_max_valid[float_sel]

        packed_float_value = _pack_float(sign, exponent, mantissa, f64=(float_sel == 1))
        if float_sel == 0 and self.rand_prob(self.p_boxed):
            packed_float_value = (packed_float_value & 0xFFFFFFFF) | self.boxed_value
        return packed_float_value & MASK_64_BIT

    def gen_any(self, **kwargs: Any) -> int:
        self.reset()
        return self.gen(**kwargs)

    def gen_f64(self, **kwargs: Any) -> int:
        self.reset()
        self.p_f64 = 1.0
        return self.gen(**kwargs)

    def gen_f32(self, **kwargs: Any) -> int:
        self.reset()
        self.p_f64 = 0.0
        return self.gen(**kwargs)

    def gen_num(self, **kwargs: Any) -> int:
        self.reset()
        self.w_ftype = {"NUM": 1}
        return self.gen(**kwargs)


_OPERAND_ALIASES = {"dest": "rd", "src1": "rs1", "src2": "rs2", "shamt": "imm"}


def encode_instr(tibbar: object, mnemonic: str, **operand_values: int) -> int:
    """Encode an instruction to 32-bit opcode."""
    resolved = {}
    for k, v in operand_values.items():
        resolved[_OPERAND_ALIASES.get(k, k)] = v
    instr = tibbar.instrs[mnemonic]
    instance = InstructionInstance(
        instruction=instr,
        operand_values=resolved,
    )
    return instance.to_opc()


def get_min_max_values(instr: object) -> tuple[int, int]:
    """Return (min_offset, max_offset) in bytes for JAL/B-type immediate range."""
    fmt = getattr(instr, "format", None)
    if fmt is None:
        return (-(2**20), 2**20 - 2)
    fmt_name = getattr(fmt, "name", None)
    if fmt_name == "J":
        # J-type: 21-bit signed, scaled by 2 (byte offset)
        return (-(2**20), 2**20 - 2)
    if fmt_name == "B":
        # B-type: 13-bit signed, scaled by 2
        return (-(2**12), 2**12 - 2)
    return (-(2**20), 2**20 - 2)
