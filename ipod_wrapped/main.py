#!/usr/bin/env python3
"""
iPod Wrapped - Main Entry Point

Usage:
    python main.py
"""
import os

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    from frontend.app import run
    run()
