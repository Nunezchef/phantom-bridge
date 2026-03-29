#!/bin/bash
# Launch Chrome in a way that survives A0's process management.
# Called by bridge.py — args are passed through.
exec setsid "$@" </dev/null >/dev/null 2>&1
