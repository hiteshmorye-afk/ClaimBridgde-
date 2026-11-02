with open("backend/app/information_extractor.py", "rb") as f:
    data = f.read()

# Replace the broken string literal
old_bytes = b'diag_match = re.search(r"(?:Clinical\\s+Diagnosis|Provisional\\s+Diagnosis|Diagnosis)\\s*[:\\-]\\s*([^\n]+)", normalized_text, flags=re.IGNORECASE)'
old_bytes_crlf = b'diag_match = re.search(r"(?:Clinical\\s+Diagnosis|Provisional\\s+Diagnosis|Diagnosis)\\s*[:\\-]\\s*([^\r\n]+)", normalized_text, flags=re.IGNORECASE)'

# Let's inspect bytes around 748
lines = data.split(b"\n")
for i, l in enumerate(lines):
    if b"Clinical\\s+Diagnosis" in l:
        print("Found line:", i, l)
        # Fix lines[i] and lines[i+1]
        lines[i] = b'    diag_match = re.search(r"(?:Clinical\\s+Diagnosis|Provisional\\s+Diagnosis|Diagnosis)\\s*[:\\-]\\s*([^\\r\\n]+)", normalized_text, flags=re.IGNORECASE)\r'
        if lines[i+1].startswith(b']+")'):
            del lines[i+1]
        break

with open("backend/app/information_extractor.py", "wb") as f:
    f.write(b"\n".join(lines))

print("Fixed broken regex!")
