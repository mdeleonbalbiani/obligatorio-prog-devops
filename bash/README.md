# Script de Creación de Usuarios - Ejercicio 1

Este script permite crear múltiples usuarios en un sistema Linux a partir de un archivo de configuración.

## Requisitos

- Sistema operativo Linux
- Permisos de superusuario (root) para crear usuarios
- Comandos disponibles: `useradd`, `chpasswd`
- Bash 4.0 o superior

## Formato del archivo de usuarios

El archivo de entrada debe tener el siguiente formato por línea:

```
usuario:comentario:directorio_home:crear_home:shell
```

Donde:
- `usuario`: Nombre del usuario (obligatorio)
- `comentario`: Descripción del usuario (opcional)
- `directorio_home`: Ruta del directorio home (por defecto: /home/usuario)
- `crear_home`: "SI" para crear el directorio home, cualquier otro valor para no crearlo (opcional, por defecto: "NO")
- `shell`: Shell por defecto (opcional, por defecto: /bin/bash)

### Ejemplo de archivo de usuarios (usuarios.txt):

```
juan:Juan Perez:/home/juan:SI:/bin/bash
maria:Maria Garcia::NO:/bin/zsh
pedro:Pedro Lopez:/home/pedro:SI:
```

## Uso

```bash
sudo ./ej1_crea_usuarios.sh [OPCIONES] archivo_usuarios
```

### Opciones:
- `-i`: Modo informativo (muestra detalles de la creación de usuarios)
- `-c CONTRASEÑA`: Establece la contraseña para todos los usuarios creados

### Ejemplos:

1. Crear usuarios sin contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh usuarios.txt
   ```

2. Crear usuarios con contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh -c "P@ssw0rd" usuarios.txt
   ```

3. Ver información detallada de la creación de usuarios:
   ```bash
   sudo ./ej1_crea_usuarios.sh -i usuarios.txt
   ```

4. Combinar modo informativo con contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh -i -c "P@ssw0rd" usuarios.txt
   ```


## Códigos de Salida

- `0`: Éxito
- `1`: No se proporcionaron argumentos
- `2`: Falta contraseña después de -c
- `3`: Parámetro desconocido
- `4`: El archivo no existe
- `5`: No es un archivo regular
- `6`: Sin permisos de lectura
- `7`: Formato de línea incorrecto
- `8`: Nombre de usuario vacío

## Pruebas

### 1. Creación básica de usuarios

```bash
# Crear archivo de prueba
echo "usuario1:Usuario de Prueba 1:/home/usuario1:SI:/bin/bash" > test_usuarios.txt
echo "usuario2:Usuario de Prueba 2:/home/usuario2:NO:/bin/sh" >> test_usuarios.txt

# Ejecutar el script
sudo ./ej1_crea_usuarios.sh -i -c "Temp1234" test_usuarios.txt
```

### 2. Verificar usuarios creados

```bash
# Verificar que los usuarios existen
id usuario1
id usuario2

# Verificar directorios home (solo para usuario1)
ls -ld /home/usuario1
ls -ld /home/usuario2  # No debería existir

# Verificar shell
grep usuario1 /etc/passwd
grep usuario2 /etc/passwd
```

## Validaciones de funcionamiento

### 1. Verificación de argumentos

#### a. Sin argumentos

Comando sin argumentos debe mostrar mensaje de error y salir con código 1.

![Sin argumentos](bash/imagenes/comando-sin-arg.png)

#### b. Opción desconocida

Comando con opción desconocida debe mostrar mensaje de error y salir con código 3.

![Argumento desconocido](bash/imagenes/arg-desconocido.png)

#### c. Falta de contraseña después de -c

Comando con -c sin contraseña debe mostrar mensaje de error y salir con código 2.

![Falta contraseña](bash/imagenes/sin-pass.png)

### 2. Verificación de archivo

#### a. Archivo inexistente

Comando con archivo inexistente debe mostrar mensaje de error y salir con código 4.

![Archivo inexistente](bash/imagenes/archivo-inexistente.png)

#### b. Archivo no regular

Comando con archivo que no es regular debe mostrar mensaje de error y salir con código 5.

![Archivo no regular](bash/imagenes/archivo-no-regular.png)

#### c. Sin permisos de lectura

Comando con archivo sin permisos de lectura debe mostrar mensaje de error y salir con código 6.

![Sin permisos](bash/imagenes/sin-permisos.png)

## Notas

- Se requiere ejecutar el script con privilegios de superusuario (sudo)
- El script verifica si los usuarios ya existen antes de intentar crearlos
- En modo informativo (-i), se muestran mensajes detallados del proceso
- Las contraseñas se aplican a todos los usuarios creados durante la ejecución