# Tarea para Agente 3: StepFun (stepfun.com)

## Objetivo
Intentar iniciar sesión o registrar una cuenta en stepfun.com usando email/contraseña.

## Instrucciones

1. **Conectar al navegador:**
   Ejecuta: `agent-browser connect 9222`

2. **Navegar a StepFun:**
   Ejecuta: `agent-browser open https://www.stepfun.com`
   Espera a que cargue completamente.

3. **Verificar estado de login:**
   Ejecuta: `agent-browser snapshot -i`
   - Observa si hay formulario de login (teléfono, email, etc.)
   - Si ves un chat o interfaz principal, puede que ya haya sesión

4. **Si NO hay sesión:**
   - Toma screenshot: `agent-browser screenshot /home/vuos/code/p3/s51/screenshots/agent3_stepfun.png`
   - Analiza el formulario: ¿pide teléfono? ¿email? ¿hay opción de registrarse?
   - Busca opciones como "注册" (Register), "登录" (Login), "Sign Up"
   - Documenta lo que encuentres

5. **Reportar progreso:**
   Escribe en `/home/vuos/code/p3/s51/progress.md` en la sección "Agente 3 - StepFun":
   - Fecha/hora
   - Estado actual
   - Qué opciones de registro hay
   - Screenshots tomados
   - Observaciones relevantes

## Notas importantes
- Browser en puerto 9222 (compartido con otros agentes)
- Guarda screenshots en /home/vuos/code/p3/s51/screenshots/
- La interfaz puede estar en chino
- Usa agent-browser para navegación e interacción
- NO cierres el navegador al terminar tu tarea
