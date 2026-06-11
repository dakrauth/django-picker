import re
import sys

text = [""]
bits = iter(re.split(r"([{}])", sys.argv[1]))
for bit in bits:
    if not bit:
        continue
    if bit == "{":
        value = next(bits).split(",")
        text = [f"{t}{b}" for t in text for b in value]
        assert next(bits) == "}"
    else:
        text = [f"{t}{bit}" for t in text]

print("\n".join(text))
