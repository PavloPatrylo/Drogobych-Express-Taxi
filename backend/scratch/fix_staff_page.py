filepath = r"D:\DROGOBYCH EXPRESS TAXI\frontend\src\pages\StaffPage.jsx"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Target exact modal role selection block
target_str = """                  <option value="driver">🚕 Водій</option>
                  <option value="dispatcher">🎧 Диспетчер</option>
                  <option value="admin">👑 Власник / Адмін</option>"""

replacement_str = """                  <option value="driver">🚕 Водій</option>
                  <option value="dispatcher">🎧 Диспетчер</option>
                  <option value="admin">👑 Власник / Адмін</option>
                  <option value="passenger">🚶 Пасажир (Понизити до пасажира)</option>"""

if target_str in content:
    content = content.replace(target_str, replacement_str)
    print("Found exact modal target and replaced!")
else:
    # Try finding without emoji in case encoding differs
    target_str2 = """<option value="driver">"""
    print("Target with emoji not found directly, checking lines...")
    idx = content.find('value="formData.role"')
    if idx != -1:
        # find the </select> after idx
        end_sel = content.find('</select>', idx)
        if end_sel != -1:
            part = content[idx:end_sel]
            new_part = part.replace('<option value="admin">', '<option value="admin">... \n                  <option value="passenger">🚶 Пасажир (Понизити до пасажира)</option>')
            # let's be even simpler: insert before </select>
            content = content[:end_sel] + '                  <option value="passenger">🚶 Пасажир (Понизити до пасажира)</option>\n' + content[end_sel:]
            print("Successfully inserted passenger option before </select>!")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
