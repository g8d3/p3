# Tarea para Agente 1: DeepSeek (chat.deepseek.com)

## Objetivo
Intentar iniciar sesión o registrar una cuenta en chat.deepseek.com usando email/contraseña.

## Instrucciones

1. **Conectar al navegador:**
   ```bash
   agent-browser connect 9222
   ```

2. **Navegar a DeepSeek:**
   ```bash
   agent-browser open https://chat.deepseek.com
   ```
   Espera a que cargue completamente.

3. **Verificar estado de login:**
   ```bash
   agent-browser snapshot -i
   ```
   - Si ves un formulario de login (email, password), estás en la página correcta.
   - Si ves un chat/interfaz de usuario, ya hay sesión iniciada.

4. **Si NO hay sesión:**
   - Toma screenshot: `agent-browser screenshot /home/vuos/code/p3/s51/screenshots/agent1_deepseek.png`
   - Busca opciones de registro ("Sign up", "Register", "创建账号")
   - Si hay formulario de registro, intenta ver qué campos pide (email, teléfono, etc.)
   - Documenta todo en el archivo de progreso

5. **Reportar progreso:**
   Escribe en `/home/vuos/code/p3/s51/progress.md` en la sección "Agente 1 - DeepSeek":
   - Fecha/hora
   - Estado (logueado/no logueado/qué se encontró)
   - Si hay opción de registro por email
   - Screenshots tomados
   - Cualquier observación relevante

## Notas importantes
- El browser está en puerto 9222 con Chrome
- Los screenshots van a /home/vuos/code/p3/s51/screenshots/
- Usa agent-browser para todas las interacciones
- Si la página está en chino, usa Google Translate o intenta identificar botones por su posición
- NO cierres el navegador al terminar
