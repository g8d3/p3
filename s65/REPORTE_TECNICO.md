# Reporte Técnico v3 (Final) — CubeSandbox + s65

## Resumen

Se construyó un sistema multi-agente eficiente (`s65/`) con sandboxing
pluggable. El DockerSandbox funciona al 100% (7/7 tests). CubeSandbox
está compilado y la mayor parte del stack corre, pero el Cubelet se
niega a iniciar fuera del one-click installer oficial.

## Estado por Componente

| Componente | Estado | Detalle |
|---|---|---|
| **s65 Agent System** | ✅ 7/7 tests | TypeScript, DockerSandbox funcional |
| **CubeMaster** | ✅ | Compilado, corre, API responde |
| **cube-api** | ✅ | Compilado, corre, health OK |
| **network-agent** | ⚠️ | Corre con sudo (eBPF), health OK |
| **Cubelet** | ❌ | Crashing. Ver abajo. |
| **Templates/Sandboxes** | ❌ | Dependen de Cubelet |

## Cubelet: Bloqueo actual

El Cubelet tiene un startup complejo que depende de:

1. **Mount namespace** (`startSelf` / `newCubeMnt`):
   - Se re-ejecuta a sí mismo con `NEED_SET_MNT` para crear un namespace
     de montaje aislado. Esto requiere `CAP_SYS_ADMIN` y puede fallar en
     entornos rootless Docker o sin permisos de mount.
   - Si falla, el proceso muere sin logs útiles.

2. **Config en formato containerd**:
   - Usa `--config` que por defecto apunta a `/etc/containerd/config.toml`
   - El formato interno mezcla campos de containerd con campos propios
     (CubeTap, DynamicConfigPath, etc.)
   - Sin el config correcto, el Action handler recibe un objeto nil o mal
     inicializado y paniquea.

3. **DynamicConfPath hardcodeado**:
   - `DynamicConfigPath` tiene default: `/usr/local/services/.../conf.yaml`
   - Si el archivo no existe o tiene formato incorrecto, `dynamConf.Init()`
     falla.

4. **Plugin storage init crash**:
   - `plugin storage init fail: quantities must match the regular
     expression` — error interno de Kubernetes resource quantity parsing,
     probablemente triggered por un valor inválido en la quota del host.

## Stack trace del crash

```
github.com/urfave/cli/v2.(*App).Run(...)
main.main()
    cubelet/cmd/cubelet/main.go:106
```

## Conclusión

CubeSandbox es una plataforma de infraestructura diseñada para
despliegue con el one-click installer en OpenCloudOS 9. Su binario
Cubelet tiene dependencias de entorno (containerd, mount namespaces,
eBPF, configs en rutas fijas) que no se pueden replicar fácilmente
fuera de ese contexto.

Para el objetivo del proyecto (sistema multi-agente eficiente), la
opción recomendada es:

**Usar DockerSandbox (ya funcional) para desarrollo, y considerar
CubeSandbox solo cuando se tenga un servidor dedicado con OpenCloudOS 9
o Ubuntu server con el one-click installer oficial.**
