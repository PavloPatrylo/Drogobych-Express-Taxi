import re

filepath = r"D:\DROGOBYCH EXPRESS TAXI\frontend\src\pages\CrmPage.jsx"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Add handleRoleChange
role_change_func = """  const handleRoleChange = async (user, newRole) => {
    if (newRole === user.role) return;
    try {
      await api.post(`/passengers/${user.id}/role`, { role: newRole });
      fetchPassengers();
    } catch (err) {
      alert(`Помилка зміни ролі: ${err.message}`);
    }
  };

  const handleToggleBlock = async (user) => {"""

content = content.replace("  const handleToggleBlock = async (user) => {", role_change_func)

# Replace table actions cell to include Role Select Dropdown
old_actions = """                        {/* Status / Toggle Block */}
                        <td className="p-4 text-right">
                          <button
                            onClick={() => handleToggleBlock(p)}"""

new_actions = """                        {/* Role & Status Actions */}
                        <td className="p-4 text-right flex items-center justify-end gap-2">
                          <select
                            value={p.role || 'passenger'}
                            onChange={(e) => handleRoleChange(p, e.target.value)}
                            className="bg-slate-950 border border-slate-800 focus:border-yellow-400 rounded-xl px-2.5 py-1 text-xs text-yellow-400 font-semibold outline-none cursor-pointer"
                            title="Змінити роль користувача"
                          >
                            <option value="passenger">🚶 Пасажир</option>
                            <option value="driver">🚕 Водій</option>
                            <option value="dispatcher">🎧 Диспетчер</option>
                            <option value="admin">👑 Адмін</option>
                          </select>
                          <button
                            onClick={() => handleToggleBlock(p)}"""

content = content.replace(old_actions, new_actions)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("CrmPage.jsx updated successfully!")
