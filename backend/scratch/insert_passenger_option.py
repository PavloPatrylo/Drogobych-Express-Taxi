filepath = r"D:\DROGOBYCH EXPRESS TAXI\frontend\src\pages\StaffPage.jsx"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if 'value="admin"' in line and '<option' in line:
        new_lines.append('                  <option value="passenger">🚶 Пасажир (Понизити до пасажира)</option>\n')

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Inserted into both selects successfully!")
