# -*- coding: utf-8 -*-

import sys


def _pause_si_exe() -> None:
    if getattr(sys, "frozen", False):
        try:
            input("\nPresione Enter para cerrar...")
        except EOFError:
            pass


def main_entry() -> None:
    from controlcomparador.app import main
    main()


if __name__ == "__main__":
    try:
        main_entry()
    except KeyboardInterrupt:
        print("\nInterrumpido.")
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        _pause_si_exe()
        sys.exit(1)
