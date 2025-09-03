import config
import gui
import argparse
import os


def getopts():
    p = argparse.ArgumentParser()
    p.add_argument('input_file', nargs='?')
    return p.parse_args()

def main():
    opts = getopts()
    conf = config.Config.load()
    gui.main(conf, opts.input_file)


if __name__ == '__main__':
    main()
