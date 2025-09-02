import config
import gui
import argparse
import os
from platformdirs import user_config_dir


def getopts():
    p = argparse.ArgumentParser()
    p.add_argument('input_file', nargs='?')
    return p.parse_args()

def main():
    opts = getopts()
    conf_file = os.path.join(user_config_dir(), "us.pixls.art.Sammy.json")
    if os.path.exists(conf_file):
        conf = config.Config.load(conf_file)
    else:
        conf = config.Config()
        try:
            conf.save(conf_file)
        except OSError:
            pass
    return gui.main(conf, opts.input_file)


if __name__ == '__main__':
    main()
