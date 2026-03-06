import sys


def main() -> None:
    if len(sys.argv) > 1:
        from cli import app
        app()
    else:
        from gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
