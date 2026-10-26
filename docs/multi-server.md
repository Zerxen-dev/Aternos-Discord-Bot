# 🗂️ Multi-Server Management Guide

Many community owners run separate servers for Survival, Creative, Minigames, or modded setups under the same Aternos account. The **Aternos Discord Bot** provides native multi-server switching without restarting the process.

---

## Commands

### 1. Listing All Available Servers
Use `/servers list` to display every Minecraft server linked to your Aternos account:
```
/servers list
```
**Example Output:**
- `[0] 🟢 survival.aternos.me (Paper 1.20.4) — [ACTIVE]`
- `[1] 🔴 creative.aternos.me (Spigot 1.20.2)`
- `[2] 🔴 skyblock.aternos.me (Fabric 1.20.1)`

### 2. Switching the Active Server
Use `/servers select` with either the server's numeric index or its subdomain:
```
/servers select identifier:creative
# or
/servers select identifier:1
```
The bot will:
1. Lock the internal state.
2. Fetch the target server's latest data.
3. Update the persistent state so that subsequent `/start`, `/stop`, `/panel`, and automation commands target the newly selected server.
4. Notify the admin with a confirmation embed.

---

## Multi-Guild Consideration

When operating across multiple Discord servers, admins can configure specific servers to monitor their respective Aternos instance or use Discord permission roles to restrict `/servers select` to trusted server operators.
