#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred. All Rights Reserved
#
# Assemble (and optionally link) a RISC-V assembly file to ELF.
# Usage: asm2elf.sh [OPTIONS] <file.S>
# Requires: RISCV_PREFIX (e.g. riscv64-unknown-elf-) and toolchain on PATH.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_LINKER_SCRIPT="$SCRIPT_DIR/riscv_bare.ld"

# Defaults
LINK=0
MARCH="${MARCH:-rv64gc}"
OUTPUT=""
LINKER_SCRIPT=""
PREFIX="${RISCV_PREFIX:-riscv64-unknown-elf-}"
# Trim trailing hyphen for consistency
PREFIX="${PREFIX%-}"
PREFIX="${PREFIX}-"

usage() {
    echo "Usage: $0 [OPTIONS] <file.S|file.s>"
    echo "  -o, --output <path>   Output file (default: input with .o or .elf)"
    echo "  --link                Link to executable ELF (entry _start)"
    echo "  --march=<value>       RISC-V arch (default: rv64gc)"
    echo "  --linker-script <ld>  Linker script path (default: sidecar <input>.ld if present, else scripts/riscv_bare.ld)"
    echo "  -h, --help            This help"
    echo ""
    echo "Environment: RISCV_PREFIX (default: riscv64-unknown-elf-)"
}

show_help() {
    usage
    exit 0
}

# Parse options and positional args
INPUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        --output=*)
            OUTPUT="${1#--output=}"
            shift
            ;;
        --link)
            LINK=1
            shift
            ;;
        --linker-script)
            LINKER_SCRIPT="$2"
            shift 2
            ;;
        --linker-script=*)
            LINKER_SCRIPT="${1#--linker-script=}"
            shift
            ;;
        --march=*)
            MARCH="${1#--march=}"
            shift
            ;;
        -h|--help)
            show_help
            ;;
        -*)
            echo "[ERROR] Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            if [[ -n "$INPUT" ]]; then
                echo "[ERROR] Multiple input files not supported: $1" >&2
                exit 1
            fi
            INPUT="$1"
            shift
            ;;
    esac
done

if [[ -z "$INPUT" ]]; then
    echo "[ERROR] No input file given." >&2
    usage
    exit 1
fi

if [[ ! -f "$INPUT" ]]; then
    echo "[ERROR] Input file not found: $INPUT" >&2
    exit 1
fi

AS="${PREFIX}as"
LD="${PREFIX}ld"
if ! command -v "$AS" &>/dev/null; then
    echo "[ERROR] RISC-V assembler not found: $AS" >&2
    echo "Install with: ./bin/install-riscv-toolchain (then use ./bin/shell)" >&2
    exit 1
fi

# Default output path
if [[ -z "$OUTPUT" ]]; then
    BASE="${INPUT%.*}"
    if [[ "$LINK" -eq 1 ]]; then
        OUTPUT="${BASE}.elf"
    else
        OUTPUT="${BASE}.o"
    fi
fi

# Assemble to object file (when linking, use a .o next to the final .elf)
OBJ="${OUTPUT}"
if [[ "$LINK" -eq 1 ]]; then
    OBJ="${OUTPUT%.*}.o"
    if [[ "$OBJ" == "$INPUT" ]]; then
        OBJ="${OUTPUT}.tmp.o"
    fi
fi

set +e
"$AS" -march="$MARCH" -o "$OBJ" "$INPUT"
AS_EXIT=$?
set -e
if [[ $AS_EXIT -ne 0 ]]; then
    echo "[ERROR] Assembler failed (exit $AS_EXIT)" >&2
    exit $AS_EXIT
fi

if [[ "$LINK" -eq 0 ]]; then
    echo "[INFO] Wrote $OUTPUT"
    exit 0
fi

# Link to executable ELF
if ! command -v "$LD" &>/dev/null; then
    echo "[ERROR] RISC-V linker not found: $LD" >&2
    rm -f "$OBJ"
    exit 1
fi

# If not explicitly set, prefer sidecar script next to input.
if [[ -z "$LINKER_SCRIPT" ]]; then
    SIDE_LD="${INPUT%.*}.ld"
    if [[ -f "$SIDE_LD" ]]; then
        LINKER_SCRIPT="$SIDE_LD"
    else
        LINKER_SCRIPT="$DEFAULT_LINKER_SCRIPT"
    fi
fi

if [[ ! -f "$LINKER_SCRIPT" ]]; then
    echo "[ERROR] Linker script not found: $LINKER_SCRIPT" >&2
    rm -f "$OBJ"
    exit 1
fi

set +e
"$LD" -T "$LINKER_SCRIPT" -o "$OUTPUT" "$OBJ" -e _start
LD_EXIT=$?
set -e
rm -f "$OBJ"
if [[ $LD_EXIT -ne 0 ]]; then
    echo "[ERROR] Linker failed (exit $LD_EXIT)" >&2
    exit $LD_EXIT
fi

echo "[INFO] Wrote $OUTPUT"
exit 0
