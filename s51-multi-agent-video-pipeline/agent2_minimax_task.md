# Tarea para Agente 2: MiniMax (minimaxi.com)

## Objetivo
Intentar iniciar sesión o registrar una cuenta en minimaxi.com usando email/contraseña.

## Instrucciones

1. **Conectar al navegador:**
   ```bash
   agent-browser connect 9222
   ```

2. **Navegar a MiniMax:**
   ```bash
   agent-browser open https://www.minimaxi.com
   ```
   Espera a que cargue completamente.

3. **Verificar estado de login:**
   ```bash
   agent-browser snapshot -i
   ```
   - Busca "平台登录" (Platform Login), "登录" (Login), o "Sign In"
   - Si ves el panel de control o chat, ya hay sesión

4. **Si NO hay sesión:**
   - Toma screenshot: `agent-browser screenshot /home/vuos/code/p3/s51/screenshots/agent2_minimax.png`
   - Haz clic en "平台登录" para ir a la página de login
   - Toma otro screenshot de la página de login
   - Busca opción de "注册" (Register) o "Sign Up"
   - Documenta qué campos pide el formulario

5. **Reportar progreso:**
   Escribe en `/home/vuos/code/p3/s51/progress.md` en la sección "Agente 2 - MiniMax":
   - Fecha/hora
   - Estado observado
   - Opciones de registro encontradas
   - Screenshots tomados
   - Observaciones

## Notas importantes
- Browser en puerto 9222
- Screenshots: /home/vuos/code/p3/s51/screenshots/
- La página está en chino principalmente
- Usa agent-browser para todo
- NO cierres el navegador
