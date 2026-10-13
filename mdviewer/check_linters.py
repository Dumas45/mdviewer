"""Module with intentional pylint warnings for testing."""

import os
import sys
import json


# W0611: Unused import (well, json is unused below)
# C0103: Constant name doesn't conform to UPPER_CASE
myConstant = 42

# C0114: Missing module docstring (we have one, so this one's fine)


def BadFunctionName(arg1, arg2, arg3, arg4, arg5, arg6):
    # C0103: Invalid function name
    # R0913: Too many arguments
    # W0621: Redefining name from outer scope (if `arg1` shadowed)
    """This function has several issues."""
    unused_variable = 100  # W0612: Unused variable
    result = arg1 + arg2
    # C0301: Line too long — this line is intentionally made very long to trigger the line-too-long warning from pylint when the default max-line-length is exceeded
    if result > 10:
        print("big")  # W1510: subprocess? no, but W0125? let's use bare print
    return result


class badClass:  # C0103: Invalid class name
    """A class with issues."""

    def __init__(self):
        # W0231: __init__ doesn't call super (if inheriting) — not applicable here
        self.x = 1
        self.y = 2

    def method(self):
        # R0201: Method could be a function (no self usage)
        return 5


def compare_to_none(value):
    """Uses `== None` instead of `is None`."""
    if value == None:  # C0121: Comparison to None should be 'if cond is None:'
        return True
    return False


def bare_except():
    """Uses a bare except clause."""
    try:
        x = 1 / 0
    except:  # W0702: No exception type(s) specified
        pass


def unreachable():
    """Has unreachable code."""
    return 1
    print("never")  # W0101: Unreachable code


def mutable_default(items=[]):  # W0102: Dangerous default value [] as argument
    items.append(1)
    return items


def string_format(name):
    """Uses old-style formatting and f-string issues."""
    # W1309: Using f-string without interpolation? No, this is fine.
    msg = "Hello %s" % name  # W1201/W1203 maybe not
    return msg


def global_abuse():
    """Modifies a global."""
    global myConstant  # W0603: Using the global statement
    myConstant = 99


def redefined_builtin(list, dict):  # W0622: Redefining built-in 'list', 'dict'
    return list, dict


def no_else_return(x):
    """Could use return directly."""
    if x > 0:
        return True
    else:  # R1705: Unnecessary "else" after "return"
        return False


def duplicate_key():
    """Has duplicate dictionary keys."""
    data = {
        "a": 1,
        "b": 2,
        "a": 3,  # W0109: Duplicate key 'a' in dictionary
    }
    return data


def exec_usage():
    """Uses exec."""
    exec("x = 1")  # W0122: Use of exec


if __name__ == "__main__":
    BadFunctionName(1, 2, 3, 4, 5, 6)
    print(compare_to_none(None))
    bare_except()
    mutable_default()
    unreachable()
    no_else_return(1)
