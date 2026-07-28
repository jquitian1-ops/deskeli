import json
import sys

def fix_json_text(text):
    """Repair invalid control chars and bad escapes in JSON strings."""
    result = []
    i = 0
    in_string = False
    escape_next = False
    while i < len(text):
        c = text[i]
        if not in_string:
            if c == '"':
                in_string = True
            result.append(c)
        else:
            if escape_next:
                # Verify valid escape target
                valid_escapes = set(['"', "\\", "/", "b", "f", "n", "r", "t", "u"])
                if c in valid_escapes:
                    result.append(c)
                else:
                    # Bad escape: turn previous \ into \\ then keep c
                    result[-1] = "\\\\"
                    result.append(c)
                escape_next = False
            elif c == "\\":
                escape_next = True
                result.append(c)
            elif c == '"':
                in_string = False
                result.append(c)
            elif ord(c) < 0x20:
                if c == "\n":
                    result.append("\\n")
                elif c == "\r":
                    result.append("\\r")
                elif c == "\t":
                    result.append("\\t")
                else:
                    result.append("\\u%04x" % ord(c))
            else:
                result.append(c)
        i += 1
    return "".join(result)


for f in sys.argv[1:]:
    with open(f, "r", encoding="utf-8") as fp:
        raw = fp.read()
    fixed = fix_json_text(raw)
    try:
        json.loads(fixed)
        with open(f, "w", encoding="utf-8", newline="") as fp:
            fp.write(fixed)
        print("FIXED: " + f)
    except json.JSONDecodeError as e:
        print("STILL BROKEN: " + f + " " + str(e))
