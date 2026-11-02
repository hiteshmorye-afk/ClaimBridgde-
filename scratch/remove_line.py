with open("backend/app/information_extractor.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for l in lines:
    if l.strip() == ']+)", normalized_text, flags=re.IGNORECASE)':
        continue
    new_lines.append(l)

with open("backend/app/information_extractor.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Line 749 removed successfully")
