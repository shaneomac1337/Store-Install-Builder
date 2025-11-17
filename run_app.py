"""
Wrapper script to run GK Install Builder with proper package imports.
This file serves as the entry point for PyInstaller builds.
"""

if __name__ == "__main__":
    from gk_install_builder.main import main
    main()
