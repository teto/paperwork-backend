#!/usr/bin/env python3

import argparse
import os
import platform
import sys

import termcolor

try:
    import paperwork.frontend.shell
    FRONTEND_COMMANDS = paperwork.frontend.shell.COMMANDS
except:
    FRONTEND_COMMANDS = {}
try:
    import paperwork_backend.shell
    BACKEND_COMMANDS = paperwork_backend.shell.COMMANDS
except:
    BACKEND_COMMANDS = {}


PACKAGE_TOOLS = {
    'debian': 'apt install',
    'fedora': 'yum install',
    'gentoo': 'emerge',
    'linuxmint': 'apt install',
    'ubuntu': 'apt install',
    'suse': 'zypper in',
}


isatty = os.isatty(sys.stdout.fileno())
verbose_enabled = False

interactive = True


def colored(txt, color):
    if isatty:
        return termcolor.colored(txt, color)
    return txt


def verbose(msg):
    if verbose_enabled:
        print(msg)


def warning(msg):
    print("[%s] %s" % (colored("WARN", "yellow"), msg))


def error(msg):
    print("[%s] %s" % (colored("ERROR", "red"), msg))


def get_distribution():
    distribution = platform.dist()
    verbose("Detected system: {}".format(" ".join(distribution)))
    distribution = distribution[0].lower()
    if distribution not in PACKAGE_TOOLS:
        warning("Unknown distribution. Can't suggest packages to install")
    return distribution


def _chkdeps(module_name, distribution):
    try:
        module = __import__(
            module_name + ".deps", globals(), locals(),
            [module_name.split('.')[-1]]
        )
    except ImportError as exc:
        error("Unable to import {}: {}".format(module_name, exc))
        sys.exit(1)
    if not hasattr(module, "find_missing_dependencies"):
        error("{} is not a Paperwork module".format(module_name))
        sys.exit(1)
    missing = module.find_missing_dependencies()

    verbose("")
    if len(missing) <= 0:
        print("All dependencies have been " + colored("found", "green") + ".")
        sys.exit(0)

    print("")
    print(colored("WARNING", "yellow") + ": Missing dependencies:")
    pkgs = []
    for dep in missing:
        if distribution in dep[2]:
            print("  - %s (python module: %s ; %s package : %s)"
                  % (dep[0], dep[1], distribution, dep[2][distribution]))
            pkgs.append(dep[2][distribution])
        else:
            print("  - %s (python module: %s)"
                  % (dep[0], dep[1]))

    if len(pkgs) > 0 and distribution in PACKAGE_TOOLS:
        command = "sudo %s %s" % (
            PACKAGE_TOOLS[distribution], " ".join(pkgs)
        )
        print("")
        print(colored("Suggested command", "yellow") + ":")
        print("  %s" % command)

        if ">" in command:
            # means there are package for which we don't know the exact name
            # so we can't run the command
            sys.exit(1)

        answer = "n"
        if interactive:
            print("Do you want to run this command now ? [Y/n]")
            answer = sys.stdin.readline().strip().lower()
        if answer == "" or answer == "y":
            r = os.system(command)
            sys.exit(r)


def chkdeps(*args):
    """
    Arguments: <component1> [<component2> [...]]]
    Look for missing dependencies.
    Ex: 'paperwork_backend',  'paperwork', 'paperwork_backend paperwork'
    """
    module_names = args
    if len(module_names) <= 0:
        error("No module specified")
        return
    distribution = get_distribution()
    for module_name in module_names:
        _chkdeps(module_name, distribution)


def cmd_help(*args):
    """
    Arguments: [<command>]
    List available commands
    """
    if len(args) == 0:
        print("Possible commands are:")
        print("")
        for cmd_name in sorted(COMMANDS.keys()):
            cmd_func = COMMANDS[cmd_name]
            print("\t{}:".format(cmd_name))
            print("{}".format(cmd_func.__doc__.strip().replace("    ", "")))
            print("")
    else:
        cmd_name = args[0]
        cmd_func = COMMANDS[cmd_name]
        print("\t{}:".format(cmd_name))
        print("{}".format(cmd_func.__doc__.strip().replace("    ", "")))


COMMANDS = {
    "chkdeps": chkdeps,
    "help": cmd_help,
}
COMMANDS.update(FRONTEND_COMMANDS)
COMMANDS.update(BACKEND_COMMANDS)


def main():
    # TODO: Interactive shell
    parser = argparse.ArgumentParser(description='Paperwork shell')
    parser.add_argument(
        'cmd', metavar="command", type=str,
        help="Command. Can be: {}".format(", ".join(COMMANDS.keys()))
    )
    parser.add_argument(
        'cmd_args', metavar="arg", type=str, nargs="*",
        help="Command arguments"
    )
    parser.add_argument('-v', dest="verbose",
                        action='store_true', help="verbose")
    parser.add_argument('-b', dest="batch",
                        action='store_true', help="non-interactive mode")
    args = parser.parse_args()
    verbose_enabled = args.verbose
    interactive = not args.batch

    os.environ['PAPERWORK_SHELL_VERBOSE'] = "True" if verbose_enabled else ""
    os.environ['PAPERWORK_INTERACTIVE'] = "True" if interactive else ""

    if args.cmd not in COMMANDS:
        print("Unknown command {}".format(args.cmd))
        cmd_help()
        sys.exit(1)

    sys.exit(COMMANDS[args.cmd](*args.cmd_args))

if __name__ == "__main__":
    main()
