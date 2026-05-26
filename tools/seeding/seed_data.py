#!/usr/bin/env python
"""
Wrapper for seed_data_consolidated.py - for backward compatibility.
This script delegates to the consolidated seed data file.

Usage:
  python tools/seeding/seed_data.py                       # Seed everything
  python tools/seeding/seed_data.py --foods               # Seed only foods
  python tools/seeding/seed_data.py --intents             # Seed only intents
  python tools/seeding/seed_data.py --patterns            # Seed only patterns
"""

if __name__ == '__main__':
    from tools.seeding.seed_data_consolidated import main

    main()
