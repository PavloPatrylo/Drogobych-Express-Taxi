import re
import os

filepath = r"D:\DROGOBYCH EXPRESS TAXI\frontend\src\pages\StaffPage.jsx"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add 'passenger' to role filter check
content = content.replace(
    "if (roleFilter === 'admin' && (member.role !== 'admin' && member.role !== 'owner')) return false;",
    "if (roleFilter === 'admin' && (member.role !== 'admin' && member.role !== 'owner')) return false;\n      if (roleFilter === 'passenger' && member.role !== 'passenger') return false;"
)

# 2. Add 'passenger' badge to getRoleBadge
passenger_badge = """      case 'passenger':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-500/10 px-2.5 py-1 rounded-lg border border-slate-500/20">
            <User size={12} /> Пасажир
          </span>
        );
      case 'driver':"""

content = content.replace("      case 'driver':", passenger_badge)

# 3. Add 'passenger' option to Role Filter select
role_filter_option = """            <option value="all">Усі ролі</option>
            <option value="driver">🚕 Водії</option>
            <option value="dispatcher">🎧 Диспетчери</option>
            <option value="admin">👑 Адміни</option>
            <option value="passenger">🚶 Пасажири</option>"""

content = re.sub(
    r'<option value="all">.*?</option>\s*<option value="driver">.*?</option>\s*<option value="dispatcher">.*?</option>\s*<option value="admin">.*?</option>',
    role_filter_option,
    content,
    flags=re.DOTALL
)

# 4. Add 'passenger' option to Modal Role Select
modal_role_options = """                  <option value="driver">🚕 Водій</option>
                  <option value="dispatcher">🎧 Диспетчер</option>
                  <option value="admin">👑 Власник / Адмін</option>
                  <option value="passenger">🚶 Пасажир (Перевести у статус пасажира)</option>"""

content = re.sub(
    r'<option value="driver">.*?</option>\s*<option value="dispatcher">.*.*?/option>\s*<option value="admin">.*?</option>',
    modal_role_options,
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("StaffPage.jsx updated successfully!")
